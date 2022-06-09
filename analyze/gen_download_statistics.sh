#!/usr/bin/env bash

log () {
    printf "[LOG] %s\n" "$1"
}


log "Begin generation"
log "Generating intermediary ISO logfile"

# Generate intermediary iso log
if [[ ! -f intermediary_isos.log ]]; then
    awk '/Rocky-8.4-(aarch64|x86_64)-.*?\.iso/ {if ($12==200 && $4!="3.134.114.30") print $0}' *.log **/*.log > intermediary_isos.log
else
    log "Skipped ISO intermediary"
fi

log "Done"
log "Generating intermediary mirrorlist stats"

# Generate intermediary mirrorlist stats
if [[ ! -f intermediary_mirrorlist.log || ! -f mirrorlist_parsed ]]; then 
    awk '/GET \/mirrorlist/ { if ($12==200 && $4!="3.134.114.30") print $0}' *.log **/*.log > intermediary_mirrorlist.log
    awk '{ date=substr($7,2,11); ip=$4; path=$10; match(path, /arch=(x86_64|aarch64|source)/, arch_matches); match(path,/repo=([a-zA-z\-0-9]+)/, repo_matches); arch=arch_matches[1]; repository=repo_matches[1] } { print date, arch, repository, ip }' intermediary_mirrorlist.log > mirrorlist_parsed
else
    log "Skipped mirrorlist intermediary"
fi


log "Done"

log "Count unique and nonunique requests"

# "Unique" count by IP addresses
totaldls_u=$(awk '{print $4}' intermediary_isos.log | sort | uniq | wc -l)

# Total count
totaldls=$(wc -l intermediary_isos.log | awk '{print $1}')


log "Generate download stats for every date"

# Get all the dates
declare -a dates
dates=( $(awk '{print substr($7,2,11)}' intermediary_isos.log | sort | uniq) )
download_res=""
for date in "${dates[@]}"; do
    total_count=$(grep "${date}" intermediary_isos.log | wc -l)
    download_res="${download_res}${date} ${total_count}\n"
done

log "Done"
log "Generate mirrorlist stats for every date"
dates=( $(awk '{print $1}' mirrorlist_parsed | sort | uniq) )
#repositories=( $(awk '{print $3}' mirrorlist_parsed | sort | uniq ) )
repositories=({AppStream,BaseOS,PowerTools,ResilientStorage,Minimal,Devel,HighAvailability,extras,rockyplus,NFV}-{8,8-source})


mirror_res="Date Total x86_64 aarch64 source ${repositories[@]}\n"
for date in "${dates[@]}"; do
    today=$(grep "${date}" mirrorlist_parsed)
        total_count=$(echo "${today}" | wc -l)
    arches=($(echo "${today}" | awk 'BEGIN {source=0; x86=0; a64=0; }{ if ($2=="x86_64") { x86+=1 } else if ($2=="aarch64") { a64+=1 } else if ($2=="source") { source+=1 } } END { print x86, a64, source }'))
    declare -A repos
    for repo in "${repositories[@]}"; do
        repos["${repo}"]=$(echo "${today}" | grep "${repo}" | wc -l)
    done
        mirror_res="${mirror_res}${date} ${total_count} ${arches[@]} ${repos[@]}\n"
done

log "Done"
log "End processing. Begin output"

# Output shit
echo -e "Download Information\n------------------"
echo -e "Total: ${totaldls}\nUnique: ${totaldls_u}\n\n\n"
echo -e "Downloads by date\n------------------"
echo -e "${download_res}" | column -t
echo -e "Mirror requests by date\n------------------"
# Sort by date
echo -e "${mirror_res}" | column -t | sort -t'/' -Mk2
