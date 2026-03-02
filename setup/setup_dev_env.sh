#!/usr/bin/env bash
#
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This script checks for and installs necessary development dependencies.
# It has special handling for declarative environments like IDX (Nix).

# --- Configuration -- -
set -e

# --- Helper Functions ---
info() { echo -e "\033[1;34m[INFO]  \033[0m $1"; }
warn() { echo -e "\033[1;33m[WARN]  \033[0m $1"; }
success() { echo -e "\033[1;32m[OK]    \033[0m $1"; }
error() { echo -e "\033[1;31m[ERROR] \033[0m $1"; }
prompt() { read -p "      $1 (y/n) " -n 1 -r; echo; }

# --- Nix/IDX Configuration ---
configure_idx() {
    local DEV_NIX_FILE=".idx/dev.nix"
    info "--- IDX Environment Detected ---"
    info "Checking dependencies in $DEV_NIX_FILE..."

    declare -A PKG_MAP
    PKG_MAP=( [gcloud]=google-cloud-sdk [make]=gnumake [git]=git [python3]=python3 [unzip]=unzip [terraform]=terraform [gh]=gh [uv]=uv [jq]=jq )
    local REQUIRED_COMMANDS=("gcloud" "make" "git" "python3" "unzip" "terraform" "gh" "uv" "jq")
    local PACKAGES_TO_ADD=()
    local dev_nix_content
    if ! dev_nix_content=$(cat "$DEV_NIX_FILE"); then
        error "Could not read .idx/dev.nix."
        exit 1
    fi

    for cmd in "${REQUIRED_COMMANDS[@]}"; do
        local pkg_name=${PKG_MAP[$cmd]}
        if ! echo "$dev_nix_content" | grep -q "pkgs\.${pkg_name}"; then
            PACKAGES_TO_ADD+=("$pkg_name")
        fi
    done

    if [ ${#PACKAGES_TO_ADD[@]} -eq 0 ]; then
        success ".idx/dev.nix already contains all required tool packages."
        configure_gcloud
        return
    fi

    warn "Your IDX environment is missing required packages."
    info "The following packages need to be added to .idx/dev.nix:"

    for pkg_to_add in "${PACKAGES_TO_ADD[@]}"; do
        echo "  - $pkg_to_add"
    done

    echo
    prompt "Add these packages to .idx/dev.nix?"
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Update skipped. The environment will not function correctly."
        exit 1
    fi

    for pkg_to_add in "${PACKAGES_TO_ADD[@]}"; do
        sed -i.bak "/^[[:space:]]*packages = \[/a \          pkgs.${pkg_to_add}" "$DEV_NIX_FILE"
    done
    rm -f "${DEV_NIX_FILE}.bak"

    success ".idx/dev.nix has been updated."
    warn "You MUST restart the IDX workspace for these changes to take effect."
    info "After restarting, run this script again to configure your Google Cloud project."
}

# --- Standard Installation Functions (for non-IDX environments) ---
install_dependency() {
  info "Installing $1...";
  if ! eval "$2"; then error "Failed to install $1." && exit 1; fi
  success "$1 installed."
}

install_homebrew() {
    info "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    local brew_path
    if [[ "$(uname -m)" == "arm64" ]]; then brew_path="/opt/homebrew/bin"; else brew_path="/usr/local/bin"; fi
    (echo; echo "eval \"$($brew_path/brew shellenv)\"") >> "$HOME/.zprofile"
    eval "$($brew_path/brew shellenv)"
    success "Homebrew installed."
}

install_from_url() {
    info "Installing $1 via curl..."
    if ! curl -LsSf "$2" | sh; then error "Failed to install $1." && exit 1; fi
    success "$1 installed. Shell may need restart."
}

install_binary() {
    info "Installing $1 via direct binary download..."
    local url=$2 ; tmp_dir=$(mktemp -d)
    info "Downloading from $url"
    curl -L -o "$tmp_dir/archive" "$url"
    case "$url" in
        *.zip) unzip "$tmp_dir/archive" -d "$tmp_dir" ;;
        *.tar.gz) tar -zxf "$tmp_dir/archive" -C "$tmp_dir" ;;
    esac
    local binary_path=$(find "$tmp_dir" -type f -name "$3" | head -n 1)
    if [ -z "$binary_path" ]; then error "$1 binary not found in archive." && exit 1; fi
    sudo mv "$binary_path" "/usr/local/bin/$3"
    rm -rf "$tmp_dir"
    success "$1 installed to /usr/local/bin/$3"
}

check_and_install() {
  info "Checking for $1..."
  if ! command -v "$2" &>/dev/null; then
    warn "$1 is not installed."
    prompt "Would you like to install it?"
    if [[ $REPLY =~ ^[Yy]$ ]]; then eval "$3"; else error "Installation skipped." && exit 1; fi
  else
    success "$1 is already installed."
  fi
}

# --- Google Cloud SDK Configuration (used by all environments) ---
configure_gcloud() {
    info "--- Google Cloud SDK Configuration ---"
    if ! command -v gcloud &>/dev/null; then
        error "gcloud command not found. Cannot configure Google Cloud."
        return 1
    fi

    info "Checking gcloud authentication..."
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "."; then
        warn "You are not authenticated with gcloud."
        info "A browser window may open to complete the login process."
        gcloud auth login --update-adc
    fi
    success "Authenticated as: $(gcloud auth list --filter=status:ACTIVE --format="value(account)")"

    info "Checking gcloud project configuration..."
    local project_id=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$project_id" ]; then
        warn "No default gcloud project is configured."
        info "Fetching available projects..."
        gcloud projects list --sort-by=projectId
        read -p "      Please enter the PROJECT_ID to use: " project_id
        if [ -z "$project_id" ]; then error "No project ID entered." && exit 1; fi
    fi
    gcloud config set project "$project_id"
    success "gcloud project set to: $project_id"

    info "Setting ADC quota project..."
    gcloud auth application-default set-quota-project "$project_id"
    success "ADC quota project set."

    if [ -f ".idx/dev.nix" ]; then
        if ! grep -q "PROJECT_ID = \"$project_id\"" ".idx/dev.nix"; then
            warn "PROJECT_ID is not declaratively set in .idx/dev.nix for persistence."
            prompt "Add PROJECT_ID to .idx/dev.nix?"
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                sed -i.bak "/^[[:space:]]*env = {/a \    PROJECT_ID = \"${project_id}\";" ".idx/dev.nix"
                rm -f ".idx/dev.nix.bak"
                success "Added PROJECT_ID to .idx/dev.nix."
                warn "You MUST restart the workspace one last time for this to take effect."
            fi
        else
            success "PROJECT_ID is correctly set in .idx/dev.nix."
        fi
    fi
}

# --- Main Script Logic ---
main() {
  if [ -f ".idx/dev.nix" ]; then
    configure_idx
    exit 0
  fi

  info "--- Standard Dependency Installation ---"
  OS="" && PACKAGE_MANAGER=""
  case "$(uname -s)" in
    Darwin) OS='macos' && PACKAGE_MANAGER='brew' ;;
    Linux) OS='linux'
      if command -v apt-get &>/dev/null; then PACKAGE_MANAGER='apt-get';
      elif command -v dnf &>/dev/null; then PACKAGE_MANAGER='dnf';
      elif command -v yum &>/dev/null; then PACKAGE_MANAGER='yum';
      fi ;;
    *) error "Unsupported OS: $(uname -s)" && exit 1 ;;
  esac

  if [[ "$OS" == "macos" ]] && ! command -v brew &>/dev/null; then
      warn "Homebrew not found."
      prompt "Install Homebrew?"
      if [[ $REPLY =~ ^[Yy]$ ]]; then install_homebrew; else error "Homebrew is required on macOS." && exit 1; fi
  fi

  # Validate that a package manager was found
  if [ -z "$PACKAGE_MANAGER" ]; then
      error "No supported package manager found (apt-get, dnf, yum, or brew). Please install dependencies manually."
      exit 1
  fi

  # Determine the correct install command based on the package manager
  local INSTALL_CMD
  if [[ "$PACKAGE_MANAGER" == "brew" ]]; then
      INSTALL_CMD="brew install"
  else
      # For Linux package managers, use sudo and assume -y flag is for non-interactive
      INSTALL_CMD="sudo $PACKAGE_MANAGER install -y"
  fi

  # Now, check and install dependencies using the determined command
  check_and_install "git" "git" "install_dependency \"git\" \"$INSTALL_CMD git\""
  check_and_install "Make" "make" "install_dependency \"Make\" \"$INSTALL_CMD make\""
  check_and_install "jq" "jq" "install_dependency \"jq\" \"$INSTALL_CMD jq\""
  check_and_install "Python 3" "python3" "install_dependency \"Python 3\" \"$INSTALL_CMD python3\""
  check_and_install "unzip" "unzip" "install_dependency \"unzip\" \"$INSTALL_CMD unzip\""

  # Binary and URL installations are independent of the package manager
  check_and_install "Terraform" "terraform" "install_binary \"Terraform\" \"https://releases.hashicorp.com/terraform/1.8.0/terraform_1.8.0_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed -e s/x86_64/amd64/ -e s/aarch64/arm64/).zip\" \"terraform\""
  check_and_install "GitHub CLI" "gh" "install_binary \"GitHub CLI\" \"https://github.com/cli/cli/releases/download/v2.45.0/gh_2.45.0_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed -e s/x86_64/amd64/ -e s/aarch64/arm64/).tar.gz\" \"gh\""
  check_and_install "uv" "uv" "install_from_url \"uv\" \"https://astral.sh/uv/install.sh\""
  check_and_install "Google Cloud SDK" "gcloud" "install_from_url \"gcloud\" \"https://sdk.cloud.google.com\""

  configure_gcloud

  echo
  success "Development environment setup complete!"
}

main "$@"

alias tf=terraform
alias more=less
