py = $(shell python3 -c "from sys import executable as ex; print(ex)" || python -c "from sys import executable as ex; print(ex)")
python = $(shell pwd)/build/venv/bin/python
pip = $(python) -m pip
dash_generate_components = $(shell pwd)/build/venv/bin/dash-generate-components

build/create_directory:
	mkdir build
	touch build/create_directory

build/venv: build/create_directory
	$(py) -m venv build/venv

build/exsclaim: build/create_directory
	cp -avru exsclaim build/exsclaim
	cp -avru requirements.txt setup.py pyproject.toml LICENSE README.md MANIFEST.in build
	cp -avru fastapi/requirements.txt build/fastapi_requirements.txt
	cp -avru dashboard/requirements.txt build/dashboard_requirements.txt
	printf "\ninclude requirements.txt\ninclude fastapi_requirements.txt\ninclude dashboard_requirements.txt\n" >> build/MANIFEST.in
	cp -avru fastapi/api build/exsclaim/api


build/app: build/exsclaim build/venv
	mkdir build/app
	$(python) -m pip install -r ./dashboard/requirements.txt
	cd build/app ; $(python) -m cookiecutter https://github.com/plotly/dash-component-boilerplate.git --no-input \
 				 project_name="EXSCLAIM UI Components" \
                 author_name="Material Eyes" \
                 author_email=developer@materialeyes.org \
                 github_org=MaterialEyes \
                 description="A UI for EXSCLAIM" \
                 use_async=False \
                 license="MIT License" \
                 publish_on_npm=False \
                 install_dependencies=False
	cp -avru dashboard/package.json build/app
	cd build/app ; npm install
	mkdir -p build/app/exsclaim_ui_components/src/lib
	cp -avru dashboard/src/components build/app/exsclaim_ui_components/src/lib/
	cp -avru dashboard/src/services build/app/exsclaim_ui_components/src/lib/
	cp -v dashboard/src/index.js build/app/exsclaim_ui_components/src/lib/index.js
	cp -avru dashboard/src/webpack.config.js build/app/exsclaim_ui_components/
	#npm run build:js --prefix=build/exsclaim_ui_components
	cd build/app/exsclaim_ui_components ; \
		npm install ; \
		$(dash_generate_components) ./src/lib/components exsclaim_ui_components -p package-info.json ; \
		npm run build:js


build/exsclaim/dashboard: build/app
	cp -avr dashboard/dashboard build/exsclaim/dashboard
	cp -avr build/app/exsclaim_ui_components/exsclaim_ui_components build/exsclaim/dashboard
	sed -i 's/include /include exsclaim\/dashboard\//g' build/app/exsclaim_ui_components/MANIFEST.in


build/exsclaim/__init__.py: build/exsclaim/dashboard
	cat build/app/exsclaim_ui_components/MANIFEST.in >> build/MANIFEST.in
	sed -i 's/fastapi\/api/exsclaim\/api/g' build/MANIFEST.in
	sed -i 's/dashboard\/dashboard/exsclaim\/dashboard/g' build/MANIFEST.in
	sed -i 's/fastapi\.api/exsclaim\.api/g' build/pyproject.toml
	sed -i 's/dashboard\.dashboard/exsclaim\.dashboard/g' build/pyproject.toml
	sed -i 's/fastapi\/requirements/fastapi_requirements/g' build/pyproject.toml
	sed -i 's/dashboard\/requirements/dashboard_requirements/g' build/pyproject.toml
	printf "\n\nfrom .api import *\nfrom .dashboard import *\n" >> build/exsclaim/__init__.py
	printf "\nfrom .exsclaim_ui_components import *\n" >> build/exsclaim/dashboard/__init__.py

build: build/exsclaim/__init__.py
	$(pip) install build
	$(python) -m build build
	cp -avru build/dist ./

install: build
	$(py) -m pip install ./dist/exsclaim*.whl
	touch build/install

clean:
	rm -rf ./build
	rm -rf ./node_modules
	rm -f ./package.json ./package-lock.json
