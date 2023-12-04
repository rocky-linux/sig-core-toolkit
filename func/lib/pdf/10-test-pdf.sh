#!/bin/bash
r_log "pdf" "Create a PDF from postscript from text, convert it back to text and check"
trap 'rm -rf $PSFILE $PDFFILE $TESTFILE' EXIT

TOFIND="BlueOnyx"
PSFILE="/var/tmp/test.ps"
PDFFILE="/var/tmp/test.pdf"
TESTFILE="/var/tmp/psresult"

encript -q -p $PSFILE /etc/rocky-release

r_log "pdf" "Check created file"

grep -q $TOFIND $PSFILE
pdf_ret_val=$?
r_checkExitStatus $pdf_ret_val

ps2pdf $PSFILE $PDFFILE
pdftotext -q $PDFFILE $TESTFILE
r_log "pdf" "Checking after conversion to text"
grep -q $TOFIND $TESTFILE
text_ret_val=$?
r_checkExitStatus $text_ret_val
