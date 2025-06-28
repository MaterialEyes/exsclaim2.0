UV := $(shell which uv)
VENV_DIR := $(shell pwd)/build/venv/bin
PYTHON := $(VENV_DIR)/python
DASH_GENERATE_COMPONENTS := $(VENV_DIR)/dash-generate-components
ifeq ($(UV),)
	# UV isn't installed
	PY := $(shell python3 -c "from sys import executable as ex; print(ex)" || python -c "from sys import executable as ex; print(ex)")
	PIP_INSTALL := $(PYTHON) -m pip install
	MAKE_VENV := $(PY) -m venv build/venv
	INSTALL_EXSCLAIM := $(PY) -m pip install ./dist/exsclaim*.whl
	BUILD := $(PYTHON) -m build
else
	# UV is installed
	PIP_INSTALL := $(UV) pip install --python $(PYTHON)
	MAKE_VENV := $(UV) venv build/venv
	INSTALL_EXSCLAIM := $(UV) pip install --system ./dist/exsclaim*.whl
	BUILD := $(UV) build
endif

build/create_directory:
	mkdir build
	touch build/create_directory

build/venv: build/create_directory
	$(MAKE_VENV)
	. $(VENV_DIR)/activate
	$(PIP_INSTALL) -r ./exsclaim/dashboard/requirements.txt

build/exsclaim: build/create_directory
	mkdir build/exsclaim
	cp -avru exsclaim/*.* exsclaim/api exsclaim/db exsclaim/captions exsclaim/figures exsclaim/tests exsclaim/utilities build/exsclaim/
	cp -avru requirements.txt setup.py pyproject.toml LICENSE README.md MANIFEST.in build
	printf "\ninclude requirements.txt\n" >> build/MANIFEST.in


build/app: build/exsclaim build/venv
	mkdir build/app
	cd build/app ; $(VENV_DIR)/cookiecutter https://github.com/plotly/dash-component-boilerplate.git --no-input \
 				 project_name="EXSCLAIM UI Components" \
				 author_name="Material Eyes" \
				 author_email=developer@materialeyes.org \
				 github_org=MaterialEyes \
				 description="A UI for EXSCLAIM" \
				 use_async=False \
				 license="MIT License" \
				 publish_on_npm=False \
				 install_dependencies=False
	cp -avru exsclaim/dashboard/package.json build/app
	cd build/app ; npm install --verbose
	mkdir -p build/app/exsclaim_ui_components/src/lib
	cp -avru exsclaim/dashboard/src/components build/app/exsclaim_ui_components/src/lib/
	cp -avru exsclaim/dashboard/src/services build/app/exsclaim_ui_components/src/lib/
	cp -v exsclaim/dashboard/src/index.js build/app/exsclaim_ui_components/src/lib/index.js
	cp -avru exsclaim/dashboard/src/webpack.config.js build/app/exsclaim_ui_components/
	cd build/app/exsclaim_ui_components ; \
		npm install --verbose ; \
		$(DASH_GENERATE_COMPONENTS) ./src/lib/components exsclaim_ui_components -p package-info.json ; \
		npm run build:js --verbose


build/exsclaim/dashboard: build/app
	mkdir build/exsclaim/dashboard
	cp -avr exsclaim/dashboard/*.py build/exsclaim/dashboard/
	cp -avr exsclaim/dashboard/assets build/exsclaim/dashboard/
	cp -avr exsclaim/dashboard/package.json build/exsclaim/dashboard/
	cp -avr build/app/exsclaim_ui_components/exsclaim_ui_components build/exsclaim/dashboard
	sed 's/exsclaim_ui_components\//exsclaim\/dashboard\/exsclaim_ui_components\//g' build/app/exsclaim_ui_components/MANIFEST.in >> build/MANIFEST.in

build: build/exsclaim/dashboard
	$(PIP_INSTALL) build
	$(BUILD) build
	cp -avru build/dist ./

install: build
	$(INSTALL_EXSCLAIM)
	touch build/install

clean:
	rm -rf ./build
	rm -rf ./node_modules
	rm -f ./package.json ./package-lock.json
