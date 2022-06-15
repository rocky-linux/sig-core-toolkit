#!/bin/bash
# You should not be running this manually.

# everything should be logged like | tee -a {{ log_path }}/lorax-{{ arch }}-{{ date_stamp }}.log
# for the dvd, we need to rely on pulling from {{ entries_root }}/dvd-{{ arch }}-list

# Run the base lorax steps into a work dir specific to its arch
# copy everything into BaseOS/arch/os
