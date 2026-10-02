SHELL := /bin/bash
.DEFAULT_GOAL := help
.NOTPARALLEL:

TERRAFORM ?= $(if $(wildcard .local/bin/terraform),$(CURDIR)/.local/bin/terraform,terraform)
PYTHON ?= python3
RUFF ?= uvx ruff==0.16.9
PLAN ?= task2.tfplan
DESTROY_PLAN ?= destroy.tfplan
REFRESH_PLAN ?= refresh.tfplan
PAUSE_PLAN ?= pause.tfplan
RESUME_PLAN ?= resume.tfplan
SINCE ?= 10m
DELAY ?= 180
export TERRAFORM PYTHON PLAN DESTROY_PLAN REFRESH_PLAN PAUSE_PLAN RESUME_PLAN SINCE DELAY
TF = "$${TERRAFORM}" -chdir=terraform
CLI = "$${PYTHON}" scripts/task2.py

.PHONY: help setup identity init init-check build format validate check test plan show-plan apply \
 output state refresh-plan refresh status subscriptions invoke verify logs logs-follow \
 demo-schedule demo-status demo-delete pause-plan pause resume-plan resume destroy-plan destroy package clean

help: ## List commands; AWS resources change only with explicit live targets
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-19s %s\n", $$1, $$2}' Makefile

setup: ## Create local terraform.tfvars if missing; edit it before planning
	@if [ -e terraform/terraform.tfvars ] || [ -L terraform/terraform.tfvars ]; then \
		echo 'Keeping existing terraform/terraform.tfvars'; \
	else cp terraform/terraform.tfvars.example terraform/terraform.tfvars; fi

identity: ## Show the AWS identity selected by AWS_PROFILE
	aws sts get-caller-identity --no-cli-pager

init: ## Initialize Terraform for deployment using the locked providers
	$(TF) init -lockfile=readonly

init-check: ## Initialize providers without a backend for local checks
	$(TF) init -backend=false -lockfile=readonly

build: ## Build the Lambda ZIP with locked Python dependencies
	"$${PYTHON}" scripts/build.py

format: ## Format Terraform and Python source
	$(TF) fmt -recursive
	$(RUFF) format src scripts tests

validate: build ## Build and validate Terraform configuration locally (run init first)
	$(TF) validate

check: validate ## Run format checks, lint and all offline tests
	$(TF) fmt -check -recursive
	$(RUFF) check src scripts tests
	$(RUFF) format --check src scripts tests
	$(TF) test
	uv run --no-project --with-requirements requirements.txt python -m unittest discover -s tests -v

test: build ## Build and run mocked Terraform and Python tests
	$(TF) test
	uv run --no-project --with-requirements requirements.txt python -m unittest discover -s tests -v

plan: build ## Build and save a deployment plan (PLAN=task2.tfplan)
	$(TF) plan -out="$${PLAN}"

show-plan: ## Display the saved deployment plan
	$(TF) show "$${PLAN}"

apply: ## Apply the previously saved PLAN immediately, using its existing ZIP
	$(TF) apply "$${PLAN}"

output: ## Show deployment outputs
	$(TF) output

state: ## List resources managed in local Terraform state
	$(TF) state list

refresh-plan: build ## Save a refresh-only plan for state/outputs
	$(TF) plan -refresh-only -out="$${REFRESH_PLAN}"

refresh: ## Apply the previously saved refresh plan
	$(TF) apply "$${REFRESH_PLAN}"

status: ## Read Lambda, daily Scheduler and SNS subscription status; save evidence
	$(CLI) status

subscriptions: ## List subscriptions; creation and email confirmation remain manual
	$(CLI) subscriptions

invoke: ## Invoke Lambda, send email to subscribers and validate the response
	$(CLI) invoke

verify: status invoke logs ## Run live status checks, send a test email and read logs

logs: ## Read recent CloudWatch logs (SINCE=10m); save evidence
	$(CLI) logs --since "$${SINCE}"

logs-follow: ## Follow CloudWatch logs until Ctrl-C (SINCE=10m)
	$(CLI) logs --since "$${SINCE}" --follow

demo-schedule: ## Schedule one test email (DELAY=180 seconds); auto-delete after completion
	$(CLI) demo-create --delay "$${DELAY}"

demo-status: ## Read the temporary demo schedule status
	$(CLI) demo-status

demo-delete: ## Delete only the temporary demo schedule, if present
	$(CLI) demo-delete

pause-plan: build ## Save a plan to disable the daily schedule
	$(TF) plan -var=schedule_enabled=false -out="$${PAUSE_PLAN}"

pause: ## Apply the saved pause plan
	$(TF) apply "$${PAUSE_PLAN}"

resume-plan: build ## Save a plan to enable the daily schedule
	$(TF) plan -var=schedule_enabled=true -out="$${RESUME_PLAN}"

resume: ## Apply the saved resume plan
	$(TF) apply "$${RESUME_PLAN}"

destroy-plan: build ## Save a destroy plan; remove any temporary demo schedule first
	$(TF) plan -destroy -out="$${DESTROY_PLAN}"

destroy: ## Apply the saved destroy plan; removes logs, topic and subscriptions
	$(TF) apply "$${DESTROY_PLAN}"

package: ## Build a source-only submission ZIP and SHA-256
	"$${PYTHON}" scripts/package.py

clean: ## Remove default ZIPs/plans; keep state, tfvars, dependencies and evidence
	"$${PYTHON}" -c 'from pathlib import Path; names = ["build/lambda.zip", "dist/GET-Task2-Lambda.zip", "dist/GET-Task2-Lambda.zip.sha256"] + ["terraform/" + name + ".tfplan" for name in ("task2", "destroy", "refresh", "pause", "resume")]; [p.unlink() for p in map(Path, names) if p.is_file() or p.is_symlink()]'
