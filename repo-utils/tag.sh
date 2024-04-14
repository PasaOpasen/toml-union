#
# tags current commit and pushes it to repo
#

set -e

cd ../

git tag "$(cat version.txt)"
git push --tags

