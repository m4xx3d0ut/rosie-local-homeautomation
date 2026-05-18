PROFILE ?= profiles/shield-k1-lineage15-dev.yaml
PROFILE_OVERLAY ?=
BUILD_DIR ?=
SERIAL ?=
INSTALL_MODE ?=
ALLOW_DESTRUCTIVE ?= 0
DRY_RUN ?= 0
PROFILE_ARGS = --profile "$(PROFILE)" $(if $(PROFILE_OVERLAY),--profile-overlay "$(PROFILE_OVERLAY)")

.PHONY: help profile-lint pin-inputs validate-inputs preflight test build-runner sync-sources extract-blobs build-images validate-emulator publish-flash-bundle device-preflight device-snapshot deploy-tablet validate-tablet collect-device-logs full-pipeline clean

help:
	@python3 tools/kioskctl.py help

profile-lint:
	@python3 tools/kioskctl.py profile-lint $(PROFILE_ARGS)

pin-inputs:
	@python3 tools/kioskctl.py pin-inputs $(PROFILE_ARGS)

validate-inputs:
	@python3 tools/kioskctl.py validate-inputs $(PROFILE_ARGS)

preflight:
	@python3 tools/kioskctl.py preflight $(PROFILE_ARGS)

test:
	@python3 -m unittest discover -s tests

build-runner:
	@python3 tools/kioskctl.py build-runner $(PROFILE_ARGS)

sync-sources:
	@python3 tools/kioskctl.py sync-sources $(PROFILE_ARGS)

extract-blobs:
	@python3 tools/kioskctl.py extract-blobs $(PROFILE_ARGS) $(if $(SERIAL),--serial "$(SERIAL)")

build-images:
	@python3 tools/kioskctl.py build-images $(PROFILE_ARGS)

validate-emulator:
	@python3 tools/kioskctl.py validate-emulator $(PROFILE_ARGS) $(if $(BUILD_DIR),--build-dir "$(BUILD_DIR)")

publish-flash-bundle:
	@python3 tools/kioskctl.py publish-flash-bundle $(PROFILE_ARGS) $(if $(BUILD_DIR),--build-dir "$(BUILD_DIR)")

device-preflight:
	@python3 tools/kioskctl.py device-preflight $(PROFILE_ARGS) $(if $(BUILD_DIR),--build-dir "$(BUILD_DIR)") $(if $(SERIAL),--serial "$(SERIAL)")

device-snapshot:
	@python3 tools/kioskctl.py device-snapshot $(PROFILE_ARGS) $(if $(BUILD_DIR),--build-dir "$(BUILD_DIR)") $(if $(SERIAL),--serial "$(SERIAL)")

deploy-tablet:
	@ALLOW_DESTRUCTIVE="$(ALLOW_DESTRUCTIVE)" python3 tools/kioskctl.py deploy-tablet $(PROFILE_ARGS) $(if $(BUILD_DIR),--build-dir "$(BUILD_DIR)") $(if $(SERIAL),--serial "$(SERIAL)") $(if $(INSTALL_MODE),--install-mode "$(INSTALL_MODE)") $(if $(filter 1 true yes,$(DRY_RUN)),--dry-run)

validate-tablet:
	@python3 tools/kioskctl.py validate-tablet $(PROFILE_ARGS) $(if $(BUILD_DIR),--build-dir "$(BUILD_DIR)") $(if $(SERIAL),--serial "$(SERIAL)")

collect-device-logs:
	@python3 tools/kioskctl.py collect-device-logs $(PROFILE_ARGS) $(if $(BUILD_DIR),--build-dir "$(BUILD_DIR)") $(if $(SERIAL),--serial "$(SERIAL)")

full-pipeline: preflight build-runner build-images validate-emulator
	@echo "Build complete and emulator validation passed."
	@echo "Deploy the WorkerBee job, then run make publish-flash-bundle after EMULATOR-VALIDATION.json reports pass."
	@echo "Physical USB deployment is gated. Run make device-preflight, then make deploy-tablet SERIAL=<serial> ALLOW_DESTRUCTIVE=1."

clean:
	@rm -rf .work/tmp
