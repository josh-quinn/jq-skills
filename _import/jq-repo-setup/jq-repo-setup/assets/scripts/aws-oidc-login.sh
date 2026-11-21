#!/bin/sh
# Exchange this job's GitHub OIDC token for short-lived AWS credentials and export them
# to later steps. No long-lived AWS keys exist anywhere. The job needs
# `permissions: id-token: write`. A shell script keeps a third-party action out of the
# deploy path (one less thing to pin and trust).
#
#   AWS_ROLE_ARN=arn:aws:iam::123456789012:role/... AWS_REGION=eu-west-1 aws-oidc-login.sh
set -eu

: "${AWS_ROLE_ARN:?AWS_ROLE_ARN is required}"
: "${AWS_REGION:?AWS_REGION is required}"
: "${ACTIONS_ID_TOKEN_REQUEST_URL:?missing id-token permission}"
: "${ACTIONS_ID_TOKEN_REQUEST_TOKEN:?missing id-token permission}"
: "${GITHUB_ENV:?must run inside GitHub Actions}"

token=$(curl -fsS -H "Authorization: Bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
  "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=sts.amazonaws.com" | jq -r .value)
echo "::add-mask::$token"

creds=$(aws sts assume-role-with-web-identity \
  --role-arn "$AWS_ROLE_ARN" \
  --role-session-name "gh-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}" \
  --web-identity-token "$token" \
  --duration-seconds 3600 \
  --region "$AWS_REGION" \
  --query Credentials --output json)

key=$(echo "$creds" | jq -r .AccessKeyId)
secret=$(echo "$creds" | jq -r .SecretAccessKey)
session=$(echo "$creds" | jq -r .SessionToken)
echo "::add-mask::$secret"
echo "::add-mask::$session"

{
  echo "AWS_ACCESS_KEY_ID=$key"
  echo "AWS_SECRET_ACCESS_KEY=$secret"
  echo "AWS_SESSION_TOKEN=$session"
  echo "AWS_DEFAULT_REGION=$AWS_REGION"
} >> "$GITHUB_ENV"
aws sts get-caller-identity --query Arn --output text
