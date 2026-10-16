"""ElevenLabs Scribe: a recording (or a pasted transcript) -> speaker-labelled transcript with every
ship, company and person on record found in it.

Scribe is biased towards names from the research index (keyterms), so obscure tanker names come out
spelled the way the sanctions data spells them. Mentions are then found in the transcript:
- IMO numbers, typed or spoken digit by digit, kept only when the IMO check digit is valid;
- names of two or more words that match a research key or an official-list name exactly;
- one-word research names (TASSOS, MERU) only next to a maritime cue, marked as a possible match,
  because many ship names are ordinary words (SUN, TRUST, HENRY).
Each mention is resolved with lookup.lookup(), so it carries the same list hits as a search.
"""
from __future__ import annotations

import re
from functools import lru_cache

from elevenlabs.client import ElevenLabs

from agent import lookup, tracing
from agent.config import env

MODEL = "scribe_v2"
MAX_KEYTERMS = 250       # Scribe allows 1000, but a long list biases it towards names nobody said
MAX_NGRAM = 6
MAX_ENTITIES = 100
CUE_WINDOW = 4

DIGITS = {"ZERO": "0", "OH": "0", "ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4",
          "FIVE": "5", "SIX": "6", "SEVEN": "7", "EIGHT": "8", "NINE": "9"}
CUES = frozenset("""TANKER TANKERS VESSEL VESSELS SHIP SHIPS BOAT CARRIER MV MT HULL IMO FLAG FLAGS FLAGGED
REFLAGGED RENAMED SANCTIONED LISTED CARGO CRUDE LNG LPG SAILED SAILING SAILS CAPTAIN CREW BERTH PORT
ANCHORED MOORED TRANSFER DARK SHADOW FLEET
LLC LTD LIMITED INC PLC GMBH PJSC JSC OJSC OOO PAO ZAO OAO LLP COMPANY FIRM OWNER OWNED MANAGER OPERATOR""".split())
_KEYTERM_BAD = re.compile(r"[<>{}\[\]\\]")
_UNITS = re.compile(r"\S+|\s+")


class ScribeUnavailable(RuntimeError):
    """No key or ElevenLabs failed; server maps this to 503."""


def imo_valid(digits: str) -> bool:
    """IMO check digit: the first six digits weighted 7..2, summed, last digit of the sum is the seventh."""
    if not (len(digits) == 7 and digits.isdigit()):
        return False
    return sum(int(d) * w for d, w in zip(digits[:6], range(7, 1, -1))) % 10 == int(digits[6])


# --- keyterms ---------------------------------------------------------------------------------------

def _clean_keyterm(term: str) -> str | None:
    term = " ".join(_KEYTERM_BAD.sub(" ", str(term or "")).split())
    if len(term) < 3 or len(term) >= 50 or len(term.split()) > 5:
        return None
    return term


@lru_cache(maxsize=1)
def _default_keyterms() -> tuple[str, ...]:
    """Current names of the most-listed research entries, ships with an IMO first."""
    research, _, _ = lookup._data()
    ranked = sorted(research, key=lambda e: (-bool(e.get("imo")), -len(e.get("listings") or []), e["name"]))
    return tuple(t for t in (_clean_keyterm(e["name"]) for e in ranked) if t)


def keyterms(hints=(), limit: int | None = None) -> list[str]:
    """User hints first (names they expect to hear), then the defaults; deduplicated, capped."""
    limit = limit if limit is not None else int(env("SCRIBE_KEYTERMS", str(MAX_KEYTERMS)))
    out, seen = [], set()
    for term in [*hints, *_default_keyterms()]:
        term = _clean_keyterm(term)
        if term and term.casefold() not in seen:
            seen.add(term.casefold())
            out.append(term)
        if len(out) >= limit:
            break
    return out


# --- transcription ----------------------------------------------------------------------------------

def transcribe(audio: bytes, filename: str = "audio", content_type: str | None = None, hints=()) -> dict:
    key = env("ELEVENLABS_API_KEY")
    if not key:
        raise ScribeUnavailable("no ELEVENLABS_API_KEY")
    terms = keyterms(hints)
    model = env("SCRIBE_MODEL", MODEL)
    try:
        res = ElevenLabs(api_key=key).speech_to_text.convert(
            model_id=model, file=(filename or "audio", audio, content_type or "application/octet-stream"),
            diarize=True, tag_audio_events=True, timestamps_granularity="word", keyterms=terms or None)
    except Exception as e:  # quota, unsupported format, network
        raise ScribeUnavailable(f"elevenlabs {type(e).__name__}: {str(e)[:200]}") from e
    words = [{"text": w.text, "type": w.type, "start": w.start, "end": w.end, "speaker": w.speaker_id}
             for w in (res.words or [])]
    return {"text": res.text, "language": res.language_code, "duration": getattr(res, "audio_duration_secs", None),
            "words": words, "model": model, "keyterms": len(terms)}


def words_from_text(text: str) -> list[dict]:
    """Pasted transcript -> the same word units Scribe returns, untimed; a blank line starts a new turn."""
    return [{"text": u, "type": "spacing" if u.isspace() else "word", "start": None, "end": None, "speaker": None}
            for u in _UNITS.findall(text or "")]


# --- mentions ---------------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _names() -> dict[str, str]:
    """Normalised name -> 'research' or 'lists'. One-word list names are left out: too many are common words."""
    research, lists, _ = lookup._data()
    index = {}
    for records in lists.values():
        for r in records:
            if r[1] and " " in r[1]:
                index[r[1]] = "lists"
    for e in research:
        for k in e["keys"]:
            index[k] = "research"
    return index


def _capitalised(word: str) -> bool:
    letters = word.lstrip("\"'([“‘")
    return bool(letters) and letters[0].isupper()


def find_mentions(words: list[dict]) -> list[dict]:
    """[{"query", "kind": "imo"|"name", "confidence": "imo"|"name"|"possible", "first", "last"}], word indices inclusive."""
    tokens = [(t, i) for i, w in enumerate(words) if w["type"] == "word" for t in lookup.normalize_name(w["text"]).split()]
    names, out, used = _names(), [], set()
    spoken = [i for i, w in enumerate(words) if w["type"] == "word"]
    pos = {w: n for n, w in enumerate(spoken)}

    def near(first, last, before, after):
        """Raw upper-case words around a span (raw, so legal suffixes such as PJSC still count)."""
        window = spoken[max(0, pos[first] - before):pos[first]] + spoken[pos[last] + 1:pos[last] + 1 + after]
        return {t for w in window for t in "".join(c if c.isalnum() else " " for c in words[w]["text"].upper()).split()}

    # IMO numbers: runs of digits or digit words ("nine four oh eight ..."), whole run or a single 7-digit token.
    i = 0
    while i < len(tokens):
        j = i
        while j < len(tokens) and (tokens[j][0].isdigit() or tokens[j][0] in DIGITS):
            j += 1
        run = tokens[i:j]
        joined = "".join(t if t.isdigit() else DIGITS[t] for t, _ in run)
        if len(joined) == 7 and imo_valid(joined):
            out.append({"query": joined, "kind": "imo", "confidence": "imo", "first": run[0][1], "last": run[-1][1],
                        "said_imo": "IMO" in near(run[0][1], run[-1][1], 2, 0)})
            used.update(range(i, j))
        else:
            for k, (t, w) in enumerate(run):
                if len(t) == 7 and imo_valid(t):
                    out.append({"query": t, "kind": "imo", "confidence": "imo", "first": w, "last": w,
                                "said_imo": "IMO" in near(w, w, 2, 0)})
                    used.add(i + k)
        i = max(j, i + 1)

    # Names: greedy longest match, never across a token already used.
    i = 0
    while i < len(tokens):
        for n in range(min(MAX_NGRAM, len(tokens) - i), 0, -1):
            span = range(i, i + n)
            if used.intersection(span):
                continue
            phrase = " ".join(tokens[k][0] for k in span)
            where = names.get(phrase)
            if not where or phrase.isdigit():
                continue
            first, last = tokens[i][1], tokens[i + n - 1][1]
            if not _capitalised(words[first]["text"]):
                continue
            if n == 1:
                if where != "research" or len(phrase) < 4 or not (near(first, last, CUE_WINDOW, CUE_WINDOW) & CUES):
                    continue
            elif len(phrase) < 6:
                continue
            out.append({"query": phrase, "kind": "name", "confidence": "possible" if n == 1 else "name",
                        "first": first, "last": last})
            used.update(span)
            i += n - 1
            break
        i += 1
    return sorted(out, key=lambda m: m["first"])


@lru_cache(maxsize=2048)
def _resolve(query: str) -> dict | None:
    """The record a mention points at, from the same lookup the search and the agent use."""
    lk = lookup.lookup(query)
    research = [r for r in lk["research"] if r["match"] == 3]
    hits = [h for h in lk["lists"] if h["match"] == 3]
    lists = [{k: h.get(k) for k in ("authority", "name", "program", "url")} for h in hits[:5]]
    authorities = {h["authority"] for h in hits}
    if research:
        top = research[0]
        return {"id": top["id"], "name": top["name"], "kind": top.get("kind"), "imo": top.get("imo"),
                "flag": top.get("flag"), "on_record": True, "lists": lists,
                "listed_by": sorted(authorities | {l["by"] for l in top.get("listings") or []}),
                "story": (top.get("story") or {}).get("url")}
    if hits:
        h = hits[0]
        return {"id": f"list:{lookup.normalize_name(h['name'])}", "name": h["name"], "kind": None, "imo": h.get("imo"),
                "flag": None, "on_record": True, "lists": lists, "listed_by": sorted(authorities), "story": None}
    if lk["imo"]:
        return {"id": f"IMO{lk['imo']}", "name": f"IMO {lk['imo']}", "kind": None, "imo": lk["imo"], "flag": None,
                "on_record": False, "lists": [], "listed_by": [], "story": None}
    return None


RANK = {"imo": 3, "name": 2, "possible": 1}


def annotate(words: list[dict]) -> dict:
    """Speaker turns split into plain text and mentions, plus one entry per distinct entity mentioned."""
    entities, by_id, at = [], {}, {}
    for m in find_mentions(words):
        rec = _resolve(m["query"])
        if not rec or (not rec["on_record"] and not m.get("said_imo")):  # an unknown 7-digit number counts only after "IMO"
            continue
        if rec["id"] not in by_id:
            if len(entities) >= MAX_ENTITIES:
                continue
            by_id[rec["id"]] = len(entities)
            entities.append({**rec, "query": rec["imo"] or rec["name"], "confidence": m["confidence"],
                             "heard_as": [], "mentions": []})
        idx = by_id[rec["id"]]
        ent = entities[idx]
        if RANK[m["confidence"]] > RANK[ent["confidence"]]:
            ent["confidence"] = m["confidence"]
        heard = "".join(w["text"] for w in words[m["first"]:m["last"] + 1]).strip(" .,;:!?\"'")
        if m["kind"] == "name" and lookup.normalize_name(heard) != lookup.normalize_name(rec["name"]) \
                and heard not in ent["heard_as"]:
            ent["heard_as"].append(heard)  # an old name or alias: said one thing, sails as another
        at[m["first"]] = (m["last"], idx)

    segments, seg = [], None
    i = 0
    while i < len(words):
        w = words[i]
        if w["type"] == "spacing" and "\n\n" in w["text"].replace("\r", ""):  # blank line in a pasted transcript
            seg, i = None, i + 1
            continue
        if seg is None or (w["type"] == "word" and w["speaker"] and w["speaker"] != seg["speaker"]):
            seg = {"speaker": w["speaker"], "start": w["start"], "end": w["end"], "parts": []}
            segments.append(seg)
        if i in at:
            last, idx = at[i]
            said = "".join(x["text"] for x in words[i:last + 1])
            core = said.rstrip(".,;:!?\"')”’")
            seg["parts"].append({"text": core, "entity": idx, "start": w["start"]})
            if core != said:
                seg["parts"].append({"text": said[len(core):]})
            end_word, i = words[last], last + 1
        else:
            if seg["parts"] and "entity" not in seg["parts"][-1]:
                seg["parts"][-1]["text"] += w["text"]
            else:
                seg["parts"].append({"text": w["text"]})
            end_word, i = w, i + 1
        if end_word["type"] != "spacing" and end_word.get("end") is not None:
            seg["end"] = end_word["end"]
    for s in segments:  # trim the whitespace a turn starts or ends with
        if s["parts"] and "entity" not in s["parts"][0]:
            s["parts"][0]["text"] = s["parts"][0]["text"].lstrip()
        if s["parts"] and "entity" not in s["parts"][-1]:
            s["parts"][-1]["text"] = s["parts"][-1]["text"].rstrip()
        s["parts"] = [p for p in s["parts"] if p["text"] or "entity" in p]
    segments = [s for s in segments if s["parts"]]

    # Listed entities first, then in the order they were first heard; renumber the transcript to match.
    for n, s in enumerate(segments):
        for p in s["parts"]:
            if "entity" in p:
                entities[p["entity"]]["mentions"].append({"start": p.pop("start"), "segment": n})
    order = sorted(range(len(entities)), key=lambda k: (-len(entities[k]["listed_by"]), entities[k]["mentions"][0]["segment"]))
    new = {old: pos for pos, old in enumerate(order)}
    for s in segments:
        for p in s["parts"]:
            if "entity" in p:
                p["entity"] = new[p["entity"]]
    return {"segments": segments, "entities": [entities[k] for k in order]}


def check_audio(audio: bytes, filename: str = "audio", content_type: str | None = None, hints=()) -> dict:
    with tracing.span("scribe", kind="TOOL", input={"filename": filename, "bytes": len(audio), "hints": list(hints)}) as s:
        t = transcribe(audio, filename, content_type, hints)
        out = {"source": "audio", "language": t["language"], "duration": t["duration"], "model": t["model"],
               "keyterms": t["keyterms"], "text": t["text"], **annotate(t["words"])}
        tracing.set_output(s, {"entities": [e["name"] for e in out["entities"]], "segments": len(out["segments"])})
        return out


def check_text(text: str) -> dict:
    return {"source": "text", "language": None, "duration": None, "model": None, "keyterms": 0, "text": text,
            **annotate(words_from_text(text))}
