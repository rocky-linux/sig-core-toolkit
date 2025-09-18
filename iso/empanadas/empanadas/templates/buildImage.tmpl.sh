#!/bin/bash

VOLID="{{ shortname }}-{{ major }}-{{ minor }}{{ rc }}-{{ arch }}-dvd"
VARIANT="{{ variant }}"
ARCH="{{ arch }}"
VERSION="{{ revision }}"
PRODUCT="{{ distname }}"
MOCKBLD="{{ builddir }}"
LORAXRES="{{ lorax_work_root }}"
LORAX_TAR="lorax-{{ revision }}-{{ arch }}.tar.gz"
LOGFILE="lorax-{{ arch }}.log"
BUGURL="{{ bugurl }}"

{% for pkg in lorax %}
sed -i '/{{ pkg }}/ s/^/#/' /usr/share/lorax/templates.d/80-rhel/runtime-install.tmpl
{% endfor %}

lorax --product="${PRODUCT}" \
  --version="${VERSION}" \
  --release="${VERSION}" \
{%- if rc == '' %}
  --isfinal \
{%- endif %}
{%- for repo in repos %}
  --source='{{ repo.url }}' \
{%- endfor %}
{%- if squashfs_only %}
  --squashfs-only \
{%- endif %}
  --bugurl="${BUGURL}" \
  --variant="${VARIANT}" \
  --nomacboot \
  --buildarch="${ARCH}" \
  --volid="${VOLID}" \
  --logfile="${MOCKBLD}/${LOGFILE}" \
  --rootfs-size=4 \
  "${LORAXRES}"

ret_val=$?
if [ $ret_val -ne 0 ]; then
  echo "!! LORAX FAILED !!"
  exit 1
fi

# If we didn't fail, let's pack up everything!
cd "${MOCKBLD}"

# Get ISO manifest
if [ -f "/usr/bin/xorriso" ]; then
    /usr/bin/xorriso -dev lorax/images/boot.iso --find |
      tail -n+2 |
      tr -d "'" |
      cut -c2-  | sort >> lorax/images/boot.iso.manifest
elif [ -f "/usr/bin/isoinfo" ]; then
    /usr/bin/isoinfo -R -f -i lorax/images/boot.iso |
      grep -v '/TRANS.TBL$' | sort >> lorax/images/boot.iso.manifest
fi

find lorax -perm 700 -exec chmod 755 {} \;

tar czf "${LORAX_TAR}" lorax "${LOGFILE}"

tar_ret_val=$?
if [ $ret_val -ne 0 ]; then
  echo "!! PROBLEM CREATING ARCHIVE !!"
  exit 1
fi

exit 0
