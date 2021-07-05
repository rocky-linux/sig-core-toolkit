#!/bin/bash
r_log "archive" "Testing lzop compress and decompress"

LZOFILE=/var/tmp/obsidian.txt

echo 'Green Obsidian is the release name' > ${LZOFILE}

# running compression
lzop -9 ${LZOFILE} -o ${LZOFILE}.lzo
/bin/rm ${LZOFILE}

lzop -d ${LZOFILE}.lzo -o ${LZOFILE}
/bin/rm ${LZOFILE}.lzo

grep -q 'Green Obsidian' ${LZOFILE}

/bin/rm ${LZOFILE}
