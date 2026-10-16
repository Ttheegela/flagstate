"""Deploy the Flagstate agent service to one EC2 instance with HTTPS, and print its URL.

    agent/.venv/bin/python -m agent.deploy_ec2

Uses the AWS credentials in agent/.env to create (once) an IAM role with Bedrock access, a security group open on
80/443, and a t3.small Amazon Linux 2023 instance. The instance clones the public repo, runs the agent behind Caddy,
which gets a Let's Encrypt certificate for <public-ip>.sslip.io. The agent calls Bedrock through the instance role,
so the AWS keys in agent/.env are not copied to the instance; the other sponsor keys are passed in user data.
"""
from __future__ import annotations

import json
import time

import boto3
import httpx

from .config import AGENT_DIR

NAME = "flagstate-agent"
REGION = "us-west-2"
REPO = "https://github.com/Ttheegela/flagstate.git"
DEPS = ("fastapi python-multipart 'uvicorn[standard]' httpx python-dotenv boto3 daytona surrealdb elevenlabs "
        "arize-otel openinference-instrumentation-bedrock opentelemetry-sdk opentelemetry-exporter-otlp")
SKIP = {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_DEFAULT_REGION", "AWS_REGION"}


def instance_env() -> str:
    lines = [l for l in (AGENT_DIR / ".env").read_text().splitlines()
             if "=" in l and not l.lstrip().startswith("#") and l.split("=", 1)[0].strip() not in SKIP]
    return "\n".join(lines + [f"AWS_REGION={REGION}"])


def user_data() -> str:
    return f"""#!/bin/bash
set -eux
dnf install -y git python3.12 python3.12-pip
git clone --depth 1 {REPO} /opt/flagstate
cd /opt/flagstate
python3.12 -m venv agent/.venv
agent/.venv/bin/pip install -q {DEPS}
cat > agent/.env <<'ENVEOF'
{instance_env()}
ENVEOF
chmod 600 agent/.env
cat > /etc/systemd/system/flagstate-agent.service <<'EOF'
[Unit]
After=network-online.target
[Service]
WorkingDirectory=/opt/flagstate
ExecStart=/opt/flagstate/agent/.venv/bin/python -m uvicorn agent.server:app --host 127.0.0.1 --port 8787
Restart=always
[Install]
WantedBy=multi-user.target
EOF
curl -fsSL "https://caddyserver.com/api/download?os=linux&arch=amd64" -o /usr/local/bin/caddy
chmod +x /usr/local/bin/caddy
TOKEN=$(curl -s -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')
IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4)
mkdir -p /etc/caddy
printf '%s.sslip.io {{\\n  reverse_proxy 127.0.0.1:8787\\n}}\\n' "${{IP//./-}}" > /etc/caddy/Caddyfile
cat > /etc/systemd/system/caddy.service <<'EOF'
[Unit]
After=network-online.target
[Service]
Environment=HOME=/root
ExecStart=/usr/local/bin/caddy run --config /etc/caddy/Caddyfile
Restart=always
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now flagstate-agent caddy
"""


def role(iam) -> str:
    try:
        iam.create_role(RoleName=NAME, AssumeRolePolicyDocument=json.dumps({"Version": "2012-10-17", "Statement": [
            {"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}]}))
        iam.put_role_policy(RoleName=NAME, PolicyName="bedrock-invoke", PolicyDocument=json.dumps({
            "Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Resource": "*", "Action": [
                "bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream", "bedrock:Converse", "bedrock:ConverseStream"]}]}))
        iam.create_instance_profile(InstanceProfileName=NAME)
        iam.add_role_to_instance_profile(InstanceProfileName=NAME, RoleName=NAME)
        time.sleep(15)  # ponytail: fixed wait for IAM propagation; poll describe if it ever races
        print("created role and instance profile", NAME)
    except iam.exceptions.EntityAlreadyExistsException:
        print("reusing role", NAME)
    return NAME


def security_group(ec2) -> str:
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    found = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [NAME]}, {"Name": "vpc-id", "Values": [vpc]}])
    if found["SecurityGroups"]:
        return found["SecurityGroups"][0]["GroupId"]
    sg = ec2.create_security_group(GroupName=NAME, Description="Flagstate agent: HTTPS only", VpcId=vpc)["GroupId"]
    ec2.authorize_security_group_ingress(GroupId=sg, IpPermissions=[
        {"IpProtocol": "tcp", "FromPort": p, "ToPort": p, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]} for p in (80, 443)])
    print("created security group", sg)
    return sg


def main() -> None:
    session = boto3.Session(region_name=REGION)
    ec2 = session.client("ec2")
    profile = role(session.client("iam"))
    sg = security_group(ec2)
    ami = session.client("ssm").get_parameter(
        Name="/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64")["Parameter"]["Value"]
    inst = ec2.run_instances(
        ImageId=ami, InstanceType="t3.small", MinCount=1, MaxCount=1, SecurityGroupIds=[sg],
        IamInstanceProfile={"Name": profile}, UserData=user_data(),
        MetadataOptions={"HttpTokens": "required"},
        TagSpecifications=[{"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": NAME}]}],
    )["Instances"][0]["InstanceId"]
    print("launched", inst)
    ec2.get_waiter("instance_running").wait(InstanceIds=[inst])
    ip = ec2.describe_instances(InstanceIds=[inst])["Reservations"][0]["Instances"][0]["PublicIpAddress"]
    url = f"https://{ip.replace('.', '-')}.sslip.io"
    print("waiting for", url)
    for _ in range(90):  # pip install + certificate take a few minutes
        try:
            if httpx.get(f"{url}/health", timeout=5).status_code == 200:
                print("AGENT_URL", url)
                return
        except httpx.HTTPError:
            pass
        time.sleep(5)
    raise SystemExit(f"no answer from {url}/health yet; instance {inst} may still be booting")


if __name__ == "__main__":
    main()
