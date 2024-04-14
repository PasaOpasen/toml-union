#
# performs minimal commit and push with default version message
# 
#
#

cd ../

git add .
git commit -m "update to $(cat version.txt)"
git push
