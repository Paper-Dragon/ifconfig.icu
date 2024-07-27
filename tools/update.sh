git submodule update --init
cd GeoLite.mmdb
git pull origin download
git submodule update --remote

# update package
pip install -r requirements.txt
pip list --outdated
pip install --upgrade <package_name>