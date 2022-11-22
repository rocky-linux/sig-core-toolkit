#!/usr/bin/env bash

VERSION="$1"
EPOCH=${EPOCH:-0}

RLVER=$VERSION

# Source common variables
# shellcheck disable=SC2046,1091,1090
source "$(dirname "${BASH_SOURCE[0]}")/common"


usage() {
  echo "usage: $0 VERSION ($0 8.7)"
}

aws() {
  command aws --region us-east-1 --profile resf-ami --output text $@
}

DATE=$(date +%Y%m%d)

if [[ -z $VERSION ]]; then
  usage
  exit 1
fi

download() {
  curl -o "$qcow" "https://dl.rockylinux.org/stg/rocky/$VERSION/images/$arch/$qcow"
  return $?
}

exists() {
  aws s3 ls $2/$1 &>/dev/null
  return $?
}

upload() {
  if exists $raw $BUCKET/$DATE; then
    echo "Found existing upload in $BUCKET"
    return 0
  fi
  aws s3 cp $raw $BUCKET/$DATE/
}

convert() {
  qemu-img convert -f qcow2 -O raw "$qcow" $raw
  return $?
}

BUCKET="s3://resf-prod-import-use1"

write-container-file() {
  printf '{"Description": "%s", "Format": "raw", "Url": "%s/%s"}\n' $name "$BUCKET/$DATE" $raw > $json
}

download-convert-upload() {
  if ! [[ -f $qcow ]]; then
    echo "Downloading $qcow from cdn"
    download || exit
  fi

  if ! [[ -f ${raw} ]]; then
    echo "Converting qcow2 $qcow to RAW $raw"
    convert || exit
  fi

  echo "Uploading raw image back to s3"
  if ! upload; then
    echo "Failed to upload"
    exit
  fi
}


begin-job() {
  import_task_id="$(aws ec2 import-snapshot --disk-container "file://$PWD/$json" --query 'ImportTaskId')"
  if [[ -z $import_task_id ]]; then
    echo "Failed to import $json"
    return 1
  fi
  echo $import_task_id
  return 0
}

is-snapshot-imported() {
  snapshot_id=$(aws ec2 describe-import-snapshot-tasks --query 'ImportSnapshotTasks[].SnapshotTaskDetail.SnapshotId[]' --import-task-ids $1)
  if [[ -z "$snapshot_id" ]]; then
    return 1
  fi
  return 0
}

register-image() {
  # Given a snapshot id, register the image
  name=$1
  snapshot_id=$2

  case $(awk -F'.' '{print $NF}'<<<"$name") in
    x86_64)
      arch=x86_64;;
    aarch64)
      arch=arm64;;
  esac

  ami_id=$(aws --query "ImageId" ec2 register-image --name "$name"  --description "$name" --block-device-mappings DeviceName="/dev/sda1",Ebs={SnapshotId="$snapshot_id"} --root-device-name "/dev/sda1" --virtualization-type hvm --architecture $arch --ena-support)

  if [[ -z "$ami_id" ]]; then
    return 1
  fi
  return 0
}

tag-resources() {
  local resources="$1"
  local tags="$2"
  if [[ -z $resources || -z $tags ]]; then
    echo "Need to provide tags and resources to tag"
    return 1
  fi
  aws ec2 create-tags --resources $resources --tags $tags
}

image-exists() {
  local RESF_AMI_ACCOUNT_ID=792107900819
  local query="$(printf 'Images[?Name==`%s`].[ImageId,Name][]' "${1}")"
  mapfile -t res < <(aws ec2 describe-images --owners $RESF_AMI_ACCOUNT_ID --query "${query}" 2>/dev/null)
  res=($res)
  if [[ ${#res[@]} -eq 0 ]]; then
    # Skip empty results
    return 1 #not found
  fi
  id=${res[0]//\"}
  name=${res[@]/$id}
  found_image_id=$id
  return 0 # found
}
snapshot-exists() {
  local RESF_AMI_ACCOUNT_ID=792107900819
  local filter="$(printf 'Name=tag:Name,Values=%s' "${1}")"
  local query='Snapshots[].[SnapshotId][]'
  mapfile -t res < <(aws ec2 describe-snapshots --owner-ids $RESF_AMI_ACCOUNT_ID --filter "${filter}" --query "${query}" 2>/dev/null)
  res=($res)
  if [[ ${#res[@]} -eq 0 ]]; then
    # Skip empty results
    return 1 #not found
  fi
  id=${res[0]//\"}
  found_snapshot_id=$id
  return 0 # found
}

declare -A import_jobs
declare -A snapshot_ids
declare -A ami_ids

TARGET_ARCHES=(x86_64 aarch64)
TARGET_VARIANTS=(Base LVM)

for variant in "${TARGET_VARIANTS[@]}"; do
  for arch in "${TARGET_ARCHES[@]}"; do
    latest=$(printf "Rocky-%s-EC2-%s.latest.%s" "$VERSION" $variant $arch)
    name=$(printf "Rocky-%s-EC2-%s-%s-%s.%s.%s" "$VERSION" $variant $REVISION $DATE $EPOCH $arch)
    qcow=${latest}.qcow2
    raw=${name}.raw
    json=${name}.json

    if image-exists $name; then
      echo "Found existing AMI in us-east-1. Skipping. ($found_image_id,$name)"
      continue
    fi

    if snapshot-exists $name; then
      # If the snapshot exists, we can skip the import task and just do the image registration
      echo "Found existing snapshot: ($found_snapshot_id,$name)"
      snapshot_ids[$name]="${found_snapshot_id}"
      continue
    fi

    # Download latest artifacts from CDN, convert from qcow2 to raw, and upload to the proper bucket
    echo "Downloading/converting artifacts for $name"
    download-convert-upload


    echo "Writing disk container json file"
    write-container-file
    
    jobid=$(begin-job)
    echo "Beginning snapshot import task with id $jobid"
    import_jobs[$name]=$jobid
  done
done

# wait for all import jobs to complete, then tag the resultant images
finished=false
while ! $finished; do
  for name in "${!import_jobs[@]}"; do
    import_task_id="${import_jobs[${name}]}"
    if ! is-snapshot-imported $import_task_id; then
      echo "Snapshot for $import_task_id ($name) is not yet finished"
      continue
    fi

    # await finalization
    sleep 2

    if [[ -z $snapshot_id ]]; then
      echo "Snapshot ID is null.. exiting"
      exit 2
    fi

    echo "Tagging snapshot with name"
    tag-resources $snapshot_id "Key=Name,Value=$name"

    unset import_jobs[${name}]
    snapshot_ids[${name}]=$snapshot_id
  done
  # Check if we're done, if so, great!
  if [[ ${#import_jobs[@]} -gt 0 ]]; then
    echo "Sleeping for 1m"
    sleep 1m
    continue
  else
    finished=true
    break
  fi
done

finished=false
while ! $finished; do
  for name in "${!snapshot_ids[@]}"; do
    # If the snapshot is imported, turn it into an AMI
    snapshot_id="${snapshot_ids[${name}]}"

    echo "Creating AMI from snapshot $snapshot_id ($name)"
    if ! register-image $name $snapshot_id; then
      echo "ERROR: Failed to create image for $name with snapshot id $snapshot_id"
      continue
    fi

    echo "Tagging AMI - Name=$name"
    tag-resources $ami_id "Key=Name,Value=$name"

    if [[ -z $ami_id ]]; then
      echo "AMI ID is null. continuing...";
      continue
    fi

    unset snapshot_ids[${name}]
    ami_ids[$name]=$ami_id
  done
  if [[ ${#snapshot_ids[@]} -gt 0 ]]; then
    sleep 1m
    continue
  else
    finished=true
    break
  fi
done

res=""
for name in "${!ami_ids[@]}"; do
  ami_id="${ami_ids[${name}]}"
  res="${res}\n$(printf '%s\t%s\n' $name $ami_id)"
done

printf "$res\n"
