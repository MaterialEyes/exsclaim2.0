UV := $(shell which uv)
VENV_DIR := $(shell pwd)/build/venv/bin
PYTHON := $(VENV_DIR)/python
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
	INSTALL_EXSCLAIM := $(UV) pip install --system --native-tls ./dist/exsclaim*.whl
	BUILD := $(UV) build
endif

build/create_directory:
	mkdir build
	touch build/create_directory

build/venv: build/create_directory
	$(MAKE_VENV)
	. $(VENV_DIR)/activate

build/exsclaim: build/create_directory
	mkdir build/exsclaim
	cp -avru exsclaim/*.* exsclaim/api exsclaim/db exsclaim/captions exsclaim/figures exsclaim/tests exsclaim/utilities build/exsclaim/
	cp -avru requirements.txt setup.py pyproject.toml LICENSE README.md MANIFEST.in build
	printf "\ninclude requirements.txt\n" >> build/MANIFEST.in

build/exsclaim/dashboard: build/exsclaim build/venv
	mkdir build/exsclaim/dashboard
	cp -avr exsclaim/dashboard/*.py build/exsclaim/dashboard/
	cp -avr exsclaim/dashboard/assets build/exsclaim/dashboard/
	cp -avr exsclaim/dashboard/components build/exsclaim/dashboard/

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
