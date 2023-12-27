#
# pushes to pypi with credentials reading
#

if [ -f pypi.sh ]
then 
    source pypi.sh
fi

U=${PYPI_USERNAME}
P=${PYPI_PASSWORD}

if [ -n "$U" ] && [ -n "$P" ]
then 
    venv/bin/python -m twine upload -u $U -p $P dist/* --skip-existing
else
    echo "credentials not found"
    venv/bin/python -m twine upload dist/* --skip-existing
fi

