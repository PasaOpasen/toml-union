#
# increases the minor version in the version.txt file
#


# https://stackoverflow.com/a/10638555/13119067

set -e

cd ../

v="$(cat version.txt)"
pre="${v%.*}"
post="${v##*.}"

(( post += 1 ))

echo -n "$pre.$post" > version.txt

