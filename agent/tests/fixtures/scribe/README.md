# Scribe samples

Synthetic recordings for "Check a recording". Each `.txt` is a script (`Speaker: line`, a blank line between turns); each `.mp3` is the same script read by ElevenLabs TTS with one voice per speaker. Speaker labels are not spoken. Regenerate the audio with `make_audio.py`.

Paste a `.txt` under "Or paste a transcript", or upload the `.mp3` (needs `ELEVENLABS_API_KEY` on the agent). `test_scribe_samples.py` checks the scripts offline.

| File | Tests | Scribe on the audio, no hints (scribe_v2, October 2026) | Hints that recover the rest |
|---|---|---|---|
| `1_news_segment` | IMO typed and spoken, an old name, a one-word company before PJSC | TASSOS (heard as Front Balder), MERU, SOVCOMFLOT (possible) | none needed |
| `2_vhf_radio_call` | radio call, spoken IMO, old names | MARIA, ENISEY (heard as Federal Baffin); "Lev Yashin" comes back as "Lev Yasin" | `Lev Yashin, Enisey, Federal Baffin` |
| `3_press_briefing` | companies, a person, ships with former names | SOVCOMFLOT, TORONTO, IMMANUEL, Admiral Group; "Ayat" and "Alexander Valerievich" missed | `Aayat Ship Management, Aleksandr Valeryevich Dyukov, Immanuel` |
| `4_court_hearing` | 3 speakers, a person, an IMO not on record | SKIF-V; "Rakhbar Madani" missed; IMO said as "twelve three four five six seven" missed | `Skif-V, Ali Rakhbarmadani` |
| `5_false_positives` | Toronto the city, Maria, Henry, sun, trust, noble, trader, new era, phone numbers, dates | nothing | nothing should match |

The pasted scripts find every name in all five, including IMO 1234567 in the court hearing.
