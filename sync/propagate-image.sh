#!/bin/bash

source_ami="$1"
source_region="${2:-us-east-1}"

if [[ -z $source_ami || -z $source_region ]]; then
	echo "usage: $0 source_ami source_region"
	exit 2
fi

RESF_AMI_ACCOUNT_ID=792107900819

REGIONS=$(aws --profile resf-ami ec2 describe-regions \
	--all-regions \
	--query "Regions[].{Name:RegionName}" \
	--output text | grep -vE "$source_region")
REGIONS="ap-southeast-4"

SOURCE_AMI_NAME=$(aws --profile resf-ami ec2 describe-images \
	--region "$source_region" --image-ids "$source_ami" --query 'Images[0].Name' \
	--output text)

# Enforce a name structure
# Rocky-8-ec2-8.6-20220515.0.x86_64
# Rocky-9-EC2-9.10-20280501.0.aarch64
# Rocky-10-EC2-10.2-20260530.0.x86_64
pat="Rocky-[0-9]{,2}-[Ee][Cc]2-(Base|LVM)-[0-9]{,2}\.[0-9]{,2}-[0-9]+\.[0-9]+\.((aarch|x86_)64)"
if [[ ! "${SOURCE_AMI_NAME}" =~ $pat ]]; then
	echo "Bad source ami (${SOURCE_AMI_NAME}). Exiting."
	exit 1
fi

function copy() {
	for region in $REGIONS; do
		if find_image_by_name $region; then
			echo "Found copy of $source_ami in $region - $found_image_id - Skipping"
			unset ami_ids[$region]
			ami_ids[$region]=$(echo $found_image_id | tr -d "'")
			continue
		fi
		echo -n "Creating copy job for $region..."
		ami_id=$(aws --profile resf-ami ec2 copy-image \
			--region $region \
			--name "${SOURCE_AMI_NAME}" \
			--source-image-id "${source_ami}" \
			--source-region "${source_region}" \
			--output text 2>&1)
		if [[ $? -eq 0 ]]; then
			unset ami_ids[$region]
			echo ". $ami_id"
			if [[ ! -z "$ami_id" ]]; then
				ami_ids[$region]="$ami_id"
			fi
			continue
		fi
		echo ".an error occurred (likely region is not signed up). Skipping."
	done
}

function change_privacy() {
	local status="$1"
	local launch_permission
	case $status in
	Private)
		launch_permission="Remove=[{Group=all}]"
		;;
	Public)
		launch_permission="Add=[{Group=all}]"
		;;
	esac
	local finished=false
	ami_ids[${source_region}]="${source_ami}"
	while ! $finished; do
		for region in "${!ami_ids[@]}"; do
			image_id=${ami_ids[$region]}
			echo -n "Making ${image_id} in $region $status..."
			if aws --profile resf-ami ec2 modify-image-attribute \
				--region $region \
				--image-id "$image_id" \
				--launch-permission "${launch_permission}" 2>/dev/null; then

				snapshot_id=$(aws --profile resf-ami ec2 describe-images \
					--region $region \
					--image-ids "${image_id}" \
					--query 'Images[*].BlockDeviceMappings[0].Ebs.SnapshotId' \
					--output text 2>&1)
				permissions=$(aws --profile resf-ami ec2 describe-snapshot-attribute \
					--region $region \
					--snapshot-id "${snapshot_id}" \
					--attribute createVolumePermission \
					--query 'CreateVolumePermissions[0].Group' \
					--output text 2>&1)
				if [[ "$permissions" == "all" ]] || aws --profile resf-ami ec2 modify-snapshot-attribute \
					--region $region \
					--snapshot-id "${snapshot_id}" \
					--create-volume-permission "${launch_permission}" 2>/dev/null; then
					unset ami_ids[$region]
					echo ". Done"
					continue
				fi
			fi
			echo ". Still pending"
		done
		if [[ ${#ami_ids[@]} -gt 0 ]]; then
			echo -n "Sleeping for one minute... "
			for ((i = 0; i < 60; i++)); do
				if [[ $((i % 10)) -eq 0 ]]; then
					echo -n "$i"
				else
					echo -n "."
				fi
				sleep 1
			done
			echo ""
		else
			finished=true
			break
		fi
	done
	echo "Completed!"
}

function find_image_by_name() {
	# found_ami_ids[region]=ami_id
	# ami-id "name"
	local query="$(printf 'Images[?Name==`%s`]|[?Public==`true`].[ImageId,Name][]' "${SOURCE_AMI_NAME}")"
	mapfile -t res < <(
		aws --profile resf-ami ec2 describe-images --region $region --owners $RESF_AMI_ACCOUNT_ID \
			--query "${query}" 2>/dev/null |
			jq -r '.|@sh'
	)
	res=($res)
	if [[ ${#res[@]} -eq 0 ]]; then
		# Skip empty results
		return 1 #not found
	fi
	id=${res[0]//\"/}
	name=${res[@]/$id/}
	# printf "Found public image: %s in %s with name '%s'\n" "$id" "$region" "${name//\"}"
	found_image_id=$id
	return 0 # found
}

declare -A ami_ids
copy
change_privacy Public # uses ami_ids
