#!/bin/bash

{% for pkg in lorax %}
sed -i '/{{ pkg }}/ s/^/#/' /usr/share/lorax/templates.d/80-rhel/runtime-install.tmpl
{% endfor %}

lorax --product='{{ distname }}' \
  --version='{{ revision }}' \
  --release='{{ revision }}' \
{%- for repo in repos %}
  --source={{ repo.url }} \
{%- endfor %}
  --variant={{ variant }} \
  --nomacboot \
  --buildarch={{ arch }} \
  --volid={{ shortname }}-{{ major }}-{{ minor }}{{ rc }}-{{ arch }}-boot1 \
  --logfile={{ mock_work_root }}/lorax.log \
  --rootfs-size=3 \
  {{ lorax_work_root }}
