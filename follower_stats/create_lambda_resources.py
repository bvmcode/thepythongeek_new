"""
Create lambda resources for automating data collection in s3
- zip file of dependencies
- policy and role
- lambda function
- cloudwatch event
"""
import json
import os
import zipfile

import boto3
from dotenv import load_dotenv

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
S3_PUT_POLICY_NAME = "S3PutPolicy"
LAMBDA_ROLE_NAME = "S3PutObjectRole"
LAMBDA_FUNCTION_NAME = "artistGetFollowers"
CLOUDWATCH_EVENT_NAME = "artist_followers_event"
CLOUDWATCH_EVENT_CADENCE = "30 03 * * ? *"

iam_client = boto3.client("iam")
lambda_client = boto3.client("lambda")
events_client = boto3.client("events")


def create_lambda_dependency_zip_file():
    """Create zip file of virtual env dependencies."""
    main_path = f"{os.getcwd()}\\"
    windows_path = f"{main_path}env\\Lib\\site-packages\\"
    zip_file_name = "function.zip"
    os.chdir(windows_path)

    with zipfile.ZipFile(zip_file_name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(windows_path, topdown=False):
            for name in files:
                if zip_file_name in name:
                    continue
                folder = root.replace(windows_path, "")
                zipf.write(os.path.join(folder, name))

    old_zip_path = windows_path + zip_file_name
    new_zip_path = main_path + zip_file_name
    os.rename(old_zip_path, new_zip_path)

    os.chdir(main_path)
    with zipfile.ZipFile(new_zip_path, "a") as zipf:
        zipf.write("lambda_function.py")


def create_s3_put_policy():
    """Create S3 write policy."""
    policy_json = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "VisualEditor0",
                "Effect": "Allow",
                "Action": "s3:PutObject",
                "Resource": "*",
            }
        ],
    }
    response = iam_client.create_policy(
        PolicyName=S3_PUT_POLICY_NAME,
        PolicyDocument=json.dumps(policy_json),
    )
    return response["Policy"]["Arn"]


def create_lambda_role():
    """Create role with S3 write permissions."""
    s3_put_policy_arn = create_s3_put_policy()
    trust_relationship = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    iam_client.create_role(
        RoleName=LAMBDA_ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(trust_relationship),
    )
    iam_client.attach_role_policy(
        PolicyArn=s3_put_policy_arn, RoleName=LAMBDA_ROLE_NAME
    )
    iam_client.attach_role_policy(
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        RoleName=LAMBDA_ROLE_NAME,
    )
    return iam_client.get_role(RoleName=LAMBDA_ROLE_NAME)


def create_lambda_function(role):
    """Create lambda function using zip file and lambda_function py file"""
    with open("function.zip", "rb") as f:
        zipped_code = f.read()

    response = lambda_client.create_function(
        FunctionName=LAMBDA_FUNCTION_NAME,
        Runtime="python3.9",
        Role=role["Role"]["Arn"],
        Handler="lambda_function.lambda_handler",
        Code=dict(ZipFile=zipped_code),
        Timeout=300,
        Environment={
            "Variables": {
                "SPOTIFY_CLIENT_ID": SPOTIFY_CLIENT_ID,
                "SPOTIFY_CLIENT_SECRET": SPOTIFY_CLIENT_SECRET,
                "TWITTER_CONSUMER_KEY": TWITTER_CONSUMER_KEY,
                "TWITTER_CONSUMER_SECRET": TWITTER_CONSUMER_SECRET,
                "TWITTER_ACCESS_TOKEN": TWITTER_ACCESS_TOKEN,
                "TWITTER_ACCESS_TOKEN_SECRET": TWITTER_ACCESS_TOKEN_SECRET,
            }
        },
    )
    return response["FunctionArn"]


def create_cloudwatch_event(lambda_arn):
    """Create cloudwatch event to schedule trigger of lambda function."""
    events_client.put_rule(
        Name=CLOUDWATCH_EVENT_NAME,
        ScheduleExpression=f"cron({CLOUDWATCH_EVENT_CADENCE})",
        State="ENABLED",
    )
    events_client.put_targets(
        Rule=CLOUDWATCH_EVENT_NAME, Targets=[{"Arn": lambda_arn, "Id": "RANDOM_ID"}]
    )
    lambda_client.add_permission(
        FunctionName=lambda_arn,
        StatementId="RANDOM_ID",
        Action="lambda:InvokeFunction",
        Principal="events.amazonaws.com",
    )


def main():
    """Execution of resource creation."""
    create_lambda_dependency_zip_file()
    role = create_lambda_role()
    lambda_arn = create_lambda_function(role)
    create_cloudwatch_event(lambda_arn)
    os.remove("function.zip")


if __name__ == "__main__":
    main()
