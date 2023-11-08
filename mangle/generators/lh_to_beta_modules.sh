function reloop_modules_to_beta() {
  FILE="${1}"
  RHELVER="${2}"
  MAJOR="$(echo ${RHELVER} | cut -d '.' -f1)"
  MINOR="$(echo ${RHELVER} | cut -d '.' -f2)"

  if [ "${#MINOR}" -eq 1 ]; then
    MINOR="0${MINOR}"
  fi

  DATE="$(date +%Y%m%d%H%M%S)"

  if [ ! -f "${FILE}" ]; then
    echo "Not a file"
    return 1
  fi

  if [ -z "$RHELVER" ]; then
    echo "verion required"
    return 1
  fi

  if [ -f "${FILE}" ]; then
    grep -q ".*:.*" ${FILE}
    ret_val=$?
    if [ $ret_val -ne 0 ]; then
      echo "File not formatted correctly"
      return 1
    fi
  fi

  for x in $(cat ${FILE}); do
    NAME=$(echo ${x} | cut -d':' -f1)
    STREAM=$(echo ${x} | cut -d':' -f2)
    TAG="imports/c${MAJOR}-beta-stream-${STREAM}/${NAME}-${STREAM}-${MAJOR}${MINOR}00${DATE}.deadbeef"
    SBRANCH="c${MAJOR}s-stream-${STREAM}"
    BRANCH="c${MAJOR}-beta-stream-${STREAM}"

    git clone ssh://src.enterpriselinux.social/modules/${NAME}.git -b "${SBRANCH}"
    if [ $? -ne 0 ]; then
      echo "!! Branch does not exist?"
      continue
    fi
    pushd ${NAME}
    git push --delete origin $(git tag | grep c${MAJOR}-beta-stream-${STREAM})
    # just in case
    git branch -D "${BRANCH}"
    git checkout -b "${BRANCH}"
    sed -i "s|ref: .*|ref: c${MAJOR}-beta-stream-${STREAM}|g" *.yaml
    git add *.yaml
    git commit -m 'update'
    git tag -a ${TAG} -m 'update'
    git push origin ${BRANCH} ${TAG} -f
    popd
    rm -rf $(pwd)/${NAME}
  done
}
