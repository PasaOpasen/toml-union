
# https://stackoverflow.com/a/10638555/13119067

v="$(cat version.txt)"
pre="${v%.*}"
post="${v##*.}"

(( post += 1 ))

echo -n "$pre.$post" > version.txt

