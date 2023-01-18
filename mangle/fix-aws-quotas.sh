#!/bin/bash

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "${BASH_SOURCE[0]}")/common"

usage() {
	echo "usage: $0"
}

aws() {
	# shellcheck disable=SC2068
	command aws --profile resf-ami --output json $@
}

# Get the quota code for Public AMIs once
quota_code=$(aws service-quotas list-service-quotas --service-code ec2 --region us-east-1 --query "Quotas[*].{QuotaCode:QuotaCode,QuotaName:QuotaName}" | jq '.[] | select(.QuotaName == "Public AMIs") | .QuotaCode' | tr -d '"')

function get_current_quota() {
	region=$1
	# Get the current value of the quota
	current_value=$(aws service-quotas get-service-quota --service-code ec2 --quota-code "$quota_code" --region "$region" 2>/dev/null | jq .Quota.Value 2>/dev/null)
	# shellcheck disable=SC2181
	if [[ $? -gt 0 ]]; then
		echo "ERR"
	fi
	echo "$current_value"
}

function request_quota_increase() {
	mapfile -t regions <<<"$@"
	for region in "${regions[@]}"; do
		# Get the current value of the quota
		current_value=$(get_current_quota "$region")
		if ((current_value >= QUOTA)); then
			echo "Quota for Public AMIs in region $region is already set to $current_value, skipping request."
		else
			# Request the quota increase
			request_output=$(aws service-quotas request-service-quota-increase --service-code ec2 --quota-code "$quota_code" --region "$region" --desired-value "$QUOTA")
			request_id=$(echo "$request_output" | jq .RequestedQuota.Id | tr -d '"')
			echo "Successfully submitted request with ID: $request_id"
		fi
	done
}

function list_quotas() {
	mapfile -t regions <<<"$@"
	output="Region\tQuota\tDesired\tStatus"
	for region in "${regions[@]}"; do
		current_quota=$(get_current_quota "$region")
		request_info=$(aws service-quotas list-requested-service-quota-change-history-by-quota --service-code ec2 --quota-code "$quota_code" --region "$region" --query "RequestedQuotas[-1:].{DesiredValue:DesiredValue,Status:Status}" 2>/dev/null)
		requested_value=$(echo "$request_info" | jq .[].DesiredValue)
		case_status=$(echo "$request_info" | jq .[].Status | tr -d '"')
		output="$output\n$region $current_quota $requested_value $case_status"
	done
	echo -e "$output" | column -t
}

REGIONS=$(aws ec2 describe-regions \
	--all-regions \
	--query "Regions[].{Name:RegionName}" \
	--output text)

QUOTA=50

list_quotas "$REGIONS"

# request_quota_increase "$REGIONS"
