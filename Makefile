py = $(shell python -c "from sys import executable as ex; print(ex)" || python3 -c "from sys import executable as ex; print(ex)")
python = ./build/venv/bin/python
pip = $(python) -m pip
dash_generate_components = $(shell pwd)/build/venv/bin/dash-generate-components

create_directory:
	mkdir build
	touch create_directory

build/venv: create_directory
	$(py) -m venv build/venv

build/exsclaim: create_directory
	cp -avru exsclaim build/exsclaim
	cp -avru requirements.txt setup.py pyproject.toml LICENSE README.md MANIFEST.in build

	cp -avru fastapi/api build/exsclaim/api


build/exsclaim_ui_components: build/exsclaim build/venv
	$(python) -m pip install -r ./dashboard/requirements.txt
	$(python) -m cookiecutter https://github.com/plotly/dash-component-boilerplate.git --no-input \
 				--output-dir ./build \
                 project_name="EXSCLAIM UI Components" \
                 author_name="Material Eyes" \
                 author_email=developer@materialeyes.org \
                 github_org=MaterialEyes \
                 description="A UI for EXSCLAIM" \
                 use_async=False \
                 license="MIT License" \
                 publish_on_npm=false \
                 install_dependencies=true
	cp -avru dashboard/package.json build/exsclaim_ui_components
	npm install ./build/exsclaim_ui_components
	mkdir -p build/exsclaim_ui_components/src/lib
	cp -avru dashboard/src/components build/exsclaim_ui_components/src/lib/components
	cp -avru dashboard/src/services build/exsclaim_ui_components/src/lib/services
	cp -avru dashboard/src/index.js build/exsclaim_ui_components/src/lib/index.js
	cp -avru dashboard/src/webpack.config.js build/exsclaim_ui_components
	npm install react-docgen@5.4.3
	$(dash_generate_components) build/exsclaim_ui_components/src/lib/components build/exsclaim_ui_components/exsclaim_ui_components -p package-info.json
	npm run build:js --prefix=build/exsclaim_ui_components

build/exsclaim/dashboard: build/exsclaim_ui_components
	cp -avr dashboard/dashboard build/exsclaim/dashboard
	cp -avr build/exsclaim_ui_components/exsclaim_ui_components build/exsclaim/dashboard/exsclaim_ui_components

build/exsclaim/__init__.py: build/exsclaim/dashboard
	cat build/exsclaim_ui_components/MANIFEST.in >> build/MANIFEST.in
	sed -i 's/fastapi\/api/exsclaim\/api/g' build/MANIFEST.in
	sed -i 's/dashboard\/dashboard/exsclaim\/dashboard/g' build/MANIFEST.in
	sed -i 's/exsclaim_ui_components/exsclaim\/dashboard\/exsclaim_ui_components/g' build/MANIFEST.in
	sed -i 's/fastapi\//exsclaim\/api\//g' build/pyproject.toml
	sed -i 's/dashboard\//exsclaim\/dashboard\//g' build/pyproject.toml
	sed -i 's/fastapi\.api/exsclaim\.api/g' build/pyproject.toml
	sed -i 's/dashboard\.dashboard/exsclaim\.dashboard/g' build/pyproject.toml
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
	rm -f create_directory