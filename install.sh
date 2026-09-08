#!/bin/bash
# =============================================================================
# Armature (OSS) Plugin Installer
# Installs Armature (OSS) as a unified plugin for Antigravity CLI, Claude Code, and Windsurf.
#
# Usage:
#   bash install.sh
#   bash install.sh --dry_run
#   bash install.sh --force
#   bash install.sh --uninstall
#   bash install.sh --update
#
# Target location:
#   ~/.gemini/config/plugins/armature-cdd/
#     ├── plugin.json
#     ├── .claude-plugin/marketplace.json
#     ├── README.md
#     ├── CHANGELOG.md
#     ├── .armature_version
#     ├── skills/
#     │   ├── arm-setup/SKILL.md (with assets/)
#     │   ├── arm-new-track/SKILL.md
#     │   ├── arm-implement/SKILL.md
#     │   ├── arm-status/SKILL.md
#     │   ├── arm-review/SKILL.md
#     │   ├── arm-revert/SKILL.md
#     │   ├── arm-drift/SKILL.md
#     │   ├── arm-chat/SKILL.md
#     │   ├── arm-new-bug-bash/SKILL.md
#     │   ├── arm-bash/SKILL.md
#     │   └── arm-bug-bash-triage/SKILL.md
#     └── rules/
#         ├── armature_protocol.md
#         ├── armature_antigravity.md
#         ├── armature_adr_preflight.md
#         └── armature_cdd_protocols.md
# =============================================================================

# --- Command line flag definitions ---
FLAGS_TRUE=0
FLAGS_FALSE=1
_DEFINED_FLAGS=()
_DEFINED_STRING_FLAGS=()

DEFINE_bool() {
  local name="$1" default="$2" desc="$3"
  if [[ "$default" == "true" ]]; then
    eval "FLAGS_${name}=${FLAGS_TRUE}"
  else
    eval "FLAGS_${name}=${FLAGS_FALSE}"
  fi
  _DEFINED_FLAGS+=("${name}|${default}|${desc}")
}

DEFINE_string() {
  local name="$1" default="$2" desc="$3"
  eval "FLAGS_${name}=\"${default}\""
  _DEFINED_STRING_FLAGS+=("${name}|${default}|${desc}")
}

parse_flags() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        echo "Usage: install.sh [OPTIONS]"
        echo ""
        echo "Options:"
        for f in "${_DEFINED_FLAGS[@]}"; do
          IFS='|' read -r fname fdef fdesc <<< "$f"
          printf "  --%-16s %s (default: %s)\n" "$fname" "$fdesc" "$fdef"
        done
        for f in "${_DEFINED_STRING_FLAGS[@]}"; do
          IFS='|' read -r fname fdef fdesc <<< "$f"
          printf "  --%-16s %s (default: %s)\n" "${fname}=<val>" "$fdesc" "$fdef"
        done
        exit 0
        ;;
      --no*)
        local flag_name="${1#--no}"
        flag_name="${flag_name//-/_}"
        eval "FLAGS_${flag_name}=${FLAGS_FALSE}"
        ;;
      --*=*)
        local flag_name="${1%%=*}"
        flag_name="${flag_name#--}"
        flag_name="${flag_name//-/_}"
        local flag_val="${1#*=}"
        eval "FLAGS_${flag_name}=\"${flag_val}\""
        ;;
      --*)
        local flag_name="${1#--}"
        flag_name="${flag_name//-/_}"
        eval "FLAGS_${flag_name}=${FLAGS_TRUE}"
        ;;
      *)
        echo "Unknown argument: $1"
        exit 1
        ;;
    esac
    shift
  done
}

DEFINE_bool dry_run false "Preview changes without writing files"
DEFINE_bool force false "Overwrite existing files without backup"
DEFINE_bool uninstall false "Remove all installed files"
DEFINE_bool update false "Update to the latest version (implies --force)"
DEFINE_string target "global" "Install target: global (default, ~/.gemini/config/plugins/armature-cdd)"
DEFINE_bool release_notes false "Show release notes for the current version"

parse_flags "$@"


VERSION="0.22.4"

# --- Resolve source directory (relative to this script) ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ASSETS_DIR="${SCRIPT_DIR}/skills/arm-setup/assets"
# Sub-skill names (each has its own directory under skills/)
SUB_SKILL_NAMES=(arm-setup arm-new-track arm-implement arm-status arm-review arm-revert arm-drift arm-chat arm-new-bug-bash arm-bash arm-bug-bash-triage)
# Rules files (always-on rule files for MVC architecture)
SOURCE_RULES_DIR="${SCRIPT_DIR}/rules"
RULE_FILE_NAMES=(armature_protocol.md armature_antigravity.md)
# Reference files (inert protocol extensions loaded on demand by skills)
REFERENCE_FILE_NAMES=(armature_adr_preflight.md armature_cdd_protocols.md)
# CHANGELOG for release notes extraction
SOURCE_CHANGELOG="${SCRIPT_DIR}/CHANGELOG.md"

# ── Color System (cli-output-hierarchy) ─────────────────────────────
#   BOLD     = structural labels, headings, emphasis
#   DIM      = secondary/explanatory text
#   CYAN     = actionable values (URLs, commands, version names, paths)
#   GREEN    = safe/positive states (success, enabled, included)
#   YELLOW   = caution, attention-needed (warnings, skipped, stripped)
#   RED BOLD = danger only (errors, emergency gates, destructive actions)
# ────────────────────────────────────────────────────────────────────
BOLD='\033[1m'
DIM='\033[2m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
RESET='\033[0m'
NC='\033[0m'

msg_info()    { echo -e "📋  $*"; }
msg_success() { echo -e "${GREEN}✅${RESET}  $*"; }
msg_warn()    { echo -e "${YELLOW}⚠️${RESET}  $*"; }
msg_error()   { echo -e "${RED}${BOLD}❌  $*${RESET}"; }
msg_skip()    { echo -e "${DIM}⏭️   $*${RESET}"; }

banner() {
  echo ""
  echo -e "${CYAN}══════════════════════════════════════════════════════${RESET}"
  echo -e "${BOLD}Armature (OSS) Installer${RESET}  ${CYAN}v${VERSION}${RESET}"
  echo -e "${DIM}Structural Permanence for AI Coding Agents${RESET}"
  echo -e "${CYAN}══════════════════════════════════════════════════════${RESET}"
  echo ""
}

section() {
  echo ""
  echo -e "${BOLD}$*${RESET}"
  echo -e "${CYAN}══════════════════════════════════════════════════════${RESET}"
  echo ""
}


# --- Validate source files exist ---
validate_sources() {
  local missing=0
  if [[ ! -f "${SOURCE_ASSETS_DIR}/workflow_template.md" ]]; then
    msg_error "Source not found: ${SOURCE_ASSETS_DIR}/workflow_template.md"
    ((missing++))
  fi
  if [[ ! -f "${SOURCE_ASSETS_DIR}/adr_template.md" ]]; then
    msg_error "Source not found: ${SOURCE_ASSETS_DIR}/adr_template.md"
    ((missing++))
  fi
  if [[ ! -f "${SOURCE_ASSETS_DIR}/manual_testing_template.md" ]]; then
    msg_error "Source not found: ${SOURCE_ASSETS_DIR}/manual_testing_template.md"
    ((missing++))
  fi
  for sub_skill in "${SUB_SKILL_NAMES[@]}"; do
    if [[ ! -f "${SCRIPT_DIR}/skills/${sub_skill}/SKILL.md" ]]; then
      msg_error "Source not found: ${SCRIPT_DIR}/skills/${sub_skill}/SKILL.md"
      ((missing++))
    fi
  done
  for rule_file in "${RULE_FILE_NAMES[@]}"; do
    if [[ ! -f "${SOURCE_RULES_DIR}/${rule_file}" ]]; then
      msg_error "Source not found: ${SOURCE_RULES_DIR}/${rule_file}"
      ((missing++))
    fi
  done
  for ref_file in "${REFERENCE_FILE_NAMES[@]}"; do
    if [[ ! -f "${SOURCE_RULES_DIR}/${ref_file}" ]]; then
      msg_error "Source not found: ${SOURCE_RULES_DIR}/${ref_file}"
      ((missing++))
    fi
  done
  if [[ $missing -gt 0 ]]; then
    msg_error "Missing ${missing} source file(s). Run from the correct directory."
    exit 1
  fi
}

# =============================================================================
# Target Selection
# =============================================================================

select_target() {
  local target_choice="${FLAGS_target:-global}"

  case "$target_choice" in
    global|antigravity|antigravity|"")
      INSTALL_TARGET="global"
      TARGET_PLUGIN_DIR="${HOME}/.gemini/config/plugins/armature-cdd"
      TARGET_SKILLS_ROOT="${TARGET_PLUGIN_DIR}/skills"
      TARGET_RULES_ROOT="${TARGET_PLUGIN_DIR}/rules"
      TARGET_MANIFEST_ROOT="${TARGET_PLUGIN_DIR}"
      ;;
    gemini_coder)
      msg_warn "Gemini Coder has been retired in favor of AI IDEs."
      msg_info "AI IDEs automatically reads plugins from ~/.gemini/config/plugins/."
      msg_info "Installing to global plugin directory: ${HOME}/.gemini/config/plugins/armature-cdd"
      INSTALL_TARGET="global"
      TARGET_PLUGIN_DIR="${HOME}/.gemini/config/plugins/armature-cdd"
      TARGET_SKILLS_ROOT="${TARGET_PLUGIN_DIR}/skills"
      TARGET_RULES_ROOT="${TARGET_PLUGIN_DIR}/rules"
      TARGET_MANIFEST_ROOT="${TARGET_PLUGIN_DIR}"
      ;;
    *)
      msg_error "Invalid target '${target_choice}'. Use 'global' (or legacy aliases 'antigravity', 'antigravity')."
      exit 1
      ;;
  esac
}

# =============================================================================
# Build target file list (after target selection)
# =============================================================================

build_target_list() {
  TARGET_ASSETS_DIR="${TARGET_SKILLS_ROOT}/arm-setup/assets"
  ALL_TARGET_FILES=(
    "${TARGET_ASSETS_DIR}/workflow_template.md"
    "${TARGET_ASSETS_DIR}/adr_template.md"
    "${TARGET_ASSETS_DIR}/manual_testing_template.md"
    "${TARGET_SKILLS_ROOT}/arm-setup/.armature_version"
    "${TARGET_PLUGIN_DIR}/.armature_version"
    "${TARGET_PLUGIN_DIR}/plugin.json"
    "${TARGET_PLUGIN_DIR}/README.md"
    "${TARGET_PLUGIN_DIR}/CHANGELOG.md"
  )
  if [[ -f "${SCRIPT_DIR}/.claude-plugin/marketplace.json" ]]; then
    ALL_TARGET_FILES+=("${TARGET_PLUGIN_DIR}/.claude-plugin/marketplace.json")
  fi
  for sub_skill in "${SUB_SKILL_NAMES[@]}"; do
    ALL_TARGET_FILES+=("${TARGET_SKILLS_ROOT}/${sub_skill}/SKILL.md")
  done
  for rule_file in "${RULE_FILE_NAMES[@]}"; do
    ALL_TARGET_FILES+=("${TARGET_RULES_ROOT}/${rule_file}")
  done
  for ref_file in "${REFERENCE_FILE_NAMES[@]}"; do
    ALL_TARGET_FILES+=("${TARGET_RULES_ROOT}/${ref_file}")
  done
}

# --- Helper: install a single file ---
install_file() {
  local source="$1"
  local target="$2"
  local target_dir
  target_dir=$(dirname "$target")
  local base_name
  base_name=$(basename "$target")

  if [[ ! -d "$target_dir" ]]; then
    if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
      msg_info "${YELLOW}[dry-run]${NC} Would create directory: ${CYAN}${target_dir}${NC}"
    else
      mkdir -p "$target_dir"
      msg_info "📂 Created directory: ${CYAN}${target_dir}${NC}"
    fi
  fi

  if [[ -f "$target" ]]; then
    if diff -q "$source" "$target" &>/dev/null; then
      msg_skip "${base_name} ${DIM}(already up-to-date)${NC}"
      return 0
    fi

    if [[ "${FLAGS_force}" -ne "${FLAGS_TRUE}" ]]; then
      local backup="${target}.bak"
      if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
        msg_info "${YELLOW}[dry-run]${NC} Would backup: ${CYAN}${base_name}${NC} → ${CYAN}${base_name}.bak${NC}"
      else
        cp "$target" "$backup"
        msg_warn "💾 Backed up: ${CYAN}${base_name}${NC} → ${CYAN}${base_name}.bak${NC}"
      fi
    fi
  fi

  if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
    msg_info "${YELLOW}[dry-run]${RESET} Would install: ${CYAN}${base_name}${RESET}"
  else
    cp "$source" "$target"
    msg_success "Installed: ${CYAN}${base_name}${RESET}  →  ${DIM}${target}${RESET}"
  fi

}

# =============================================================================
# Legacy Migrations
# =============================================================================

migrate_legacy_conductor_plugin() {
  local legacy_paths=(
    "${HOME}/.gemini/config/plugins/antigravity-armature"
    "${HOME}/.gemini/config/plugins/antigravity-conductor"
    "${HOME}/.gemini/extensions/conductor"
    "${HOME}/.gemini/antigravity-cli/plugins/conductor"
  )

  local found_legacy_plugins=()
  for p in "${legacy_paths[@]}"; do
    if [[ -d "$p" ]]; then
      found_legacy_plugins+=("$p")
    fi
  done

  local enablement_file="${HOME}/.gemini/extensions/extension-enablement.json"
  local has_enablement_entry=0
  if [[ -f "$enablement_file" ]] && grep -q '"conductor"' "$enablement_file"; then
    has_enablement_entry=1
  fi

  if [[ ${#found_legacy_plugins[@]} -gt 0 || $has_enablement_entry -eq 1 ]]; then
    section "🔄 Legacy Conductor Plugin & Extension Cleanup"

    echo ""
    if [[ ${#found_legacy_plugins[@]} -gt 0 ]]; then
      msg_warn "Found ${#found_legacy_plugins[@]} legacy plugin/extension installation(s). Migrating to armature-cdd..."
      for p in "${found_legacy_plugins[@]}"; do
        if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
          msg_info "${YELLOW}[dry-run]${NC} Would remove legacy directory: ${CYAN}${p}${NC}"
        else
          rm -rf "${p}"
          msg_success "Removed legacy directory: ${CYAN}${p}${NC}"
        fi
      done
    fi

    if [[ $has_enablement_entry -eq 1 ]]; then
      if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
        msg_info "${YELLOW}[dry-run]${NC} Would remove legacy entries from: ${CYAN}${enablement_file}${NC}"
      else
        python3 -c "
import json
p = '$enablement_file'
try:
  with open(p, 'r') as f:
    data = json.load(f)
  changed = False
  for key in ['conductor']:
    if key in data:
      del data[key]
      changed = True
  if changed:
    with open(p, 'w') as f:
      json.dump(data, f, indent=2)
except Exception:
  pass
" 2>/dev/null |
        msg_success "Cleaned legacy entries from: ${CYAN}${enablement_file}${NC}"
      fi
    fi
    echo ""
  fi
}

sync_config_json_plugins() {
  local config_file="${HOME}/.gemini/config/config.json"
  if [[ -f "$config_file" ]]; then
    if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
      msg_info "${YELLOW}[dry-run]${NC} Would register plugin in: ${CYAN}${config_file}${NC}"
    else
      python3 -c "
import json
p = '$config_file'
try:
  with open(p, 'r') as f:
    data = json.load(f)
  if 'plugins' not in data:
    data['plugins'] = {}
  data['plugins']['armature-cdd'] = {'enabled': True}
  for key in ['antigravity-armature', 'antigravity-conductor']:
    if key in data['plugins']:
      del data['plugins'][key]
  with open(p, 'w') as f:
    json.dump(data, f, indent=2)
except Exception:
  pass
" 2>/dev/null |
      msg_success "Registered plugin in ${CYAN}${config_file}${NC}"
    fi
  fi
}

migrate_from_workflows() {
  local legacy_dirs=(
    "${HOME}/.gemini/antigravity/global_workflows"
    "${HOME}/.gemini/antigravity/global_workflows"
  )

  local legacy_files=()
  for dir in "${legacy_dirs[@]}"; do
    if [[ -d "$dir" ]]; then
      for wf in implement newTrack revert review setup status; do
        local legacy_file="${dir}/conductor_${wf}.md"
        if [[ -f "$legacy_file" ]]; then
          legacy_files+=("$legacy_file")
        fi
      done
    fi
  done

  if [[ ${#legacy_files[@]} -eq 0 ]]; then
    return 0
  fi

  section "🔄 Legacy Workflow Migration"
  echo ""
  msg_warn "Found ${BOLD}${#legacy_files[@]}${NC}${YELLOW} legacy Conductor workflow file(s):${NC}"
  for f in "${legacy_files[@]}"; do
    echo -e "     ${DIM}${f}${NC}"
  done
  echo ""

  if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
    for f in "${legacy_files[@]}"; do
      msg_info "${YELLOW}[dry-run]${NC} Would remove legacy workflow: ${CYAN}$(basename "$f")${NC}"
    done
    return 0
  fi

  for f in "${legacy_files[@]}"; do
    rm -f "$f"
    msg_success "Removed legacy workflow: ${CYAN}$(basename "$f")${NC}"
  done
}

migrate_from_hub_skill() {
  local hub_dirs=(
    "${HOME}/.gemini/antigravity/skills/conductor"
    "${HOME}/.gemini/antigravity/skills/conductor"
    "${HOME}/.gemini/config/skills/conductor"
  )

  for hub_dir in "${hub_dirs[@]}"; do
    if [[ -d "$hub_dir" ]]; then
      if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
        msg_info "${YELLOW}[dry-run]${NC} Would remove legacy hub skill directory: ${CYAN}${hub_dir}${NC}"
      else
        rm -rf "$hub_dir"
        msg_success "Removed legacy hub skill directory: ${CYAN}${hub_dir}${NC}"
      fi
    fi
  done
}

migrate_to_v0_11_0() {
  local old_skills=(
    "conductor_setup"
    "conductor_newTrack"
    "conductor_newTrack_grill"
    "conductor_newTrack_discovery"
    "conductor_implement"
    "conductor_status"
    "conductor_review"
    "conductor_revert"
    "conductor_chat"
  )

  local search_roots=(
    "${HOME}/.gemini/antigravity/skills"
    "${HOME}/.gemini/antigravity/skills"
    "${HOME}/.gemini/config/skills"
  )

  for root in "${search_roots[@]}"; do
    for old_skill in "${old_skills[@]}"; do
      local old_dir="${root}/${old_skill}"
      if [[ -d "$old_dir" ]]; then
        if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
          msg_info "${YELLOW}[dry-run]${NC} Would remove deprecated skill directory: ${CYAN}${old_dir}${NC}"
        else
          rm -rf "$old_dir"
          msg_success "Removed deprecated skill directory: ${CYAN}${old_dir}${NC}"
        fi
      fi
    done
  done
}

migrate_to_v0_12_0() {
  local legacy_dirs=(
    "${HOME}/.gemini/antigravity/skills"
    "${HOME}/.gemini/config/skills"
    "${HOME}/.gemini/antigravity/skills"
  )
  local skill_names=(
    "conductor"
    "conductor-setup" "conductor_setup"
    "conductor-new-track" "conductor_newTrack" "conductor_newTrack_grill" "conductor_newTrack_discovery"
    "conductor-implement" "conductor_implement"
    "conductor-status" "conductor_status"
    "conductor-review" "conductor_review"
    "conductor-revert" "conductor_revert"
    "conductor-chat" "conductor_chat"
    "gpto-setup" "gpto-new-track" "gpto-implement" "gpto-status" "gpto-review" "gpto-revert" "gpto-drift" "gpto-chat"
  )

  local found_legacy=()
  for base_dir in "${legacy_dirs[@]}"; do
    for skill_name in "${skill_names[@]}"; do
      local target_dir="${base_dir}/${skill_name}"
      if [[ -d "$target_dir" ]] && [[ "$target_dir" != "${TARGET_SKILLS_ROOT}/${skill_name}" ]]; then
        found_legacy+=("$target_dir")
      fi
    done
  done

  # Legacy rules in ~/.gemini/antigravity/rules/ or ~/.gemini/config/rules/ or ~/.gemini/antigravity/rules/
  local rule_dirs=(
    "${HOME}/.gemini/antigravity/rules"
    "${HOME}/.gemini/config/rules"
    "${HOME}/.gemini/antigravity/rules"
  )
  for base_dir in "${rule_dirs[@]}"; do
    for rf in "${RULE_FILE_NAMES[@]}" "${REFERENCE_FILE_NAMES[@]}" \
              "geppetto_protocol.md" "geppetto_antigravity.md" "geppetto_enterprise.md" "geppetto_adr_preflight.md" "geppetto_cdd_protocols.md" \
              "conductor_protocol.md" "conductor_antigravity.md" "conductor_enterprise.md" "conductor_adr_preflight.md" "conductor_cdd_protocols.md"; do
      local target_file="${base_dir}/${rf}"
      if [[ -f "$target_file" ]] && [[ "$target_file" != "${TARGET_RULES_ROOT}/${rf}" ]]; then
        found_legacy+=("$target_file")
      fi
    done
  done

  if [[ ${#found_legacy[@]} -eq 0 ]]; then
    return 0
  fi

  section "🔄 Legacy Path Migration"
  echo ""
  msg_warn "Found ${#found_legacy[@]} legacy file(s)/directory(ies) outside ${TARGET_PLUGIN_DIR}:"
  for item in "${found_legacy[@]}"; do
    echo -e "     ${DIM}${item}${NC}"
  done
  echo ""

  if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
    for item in "${found_legacy[@]}"; do
      msg_info "${YELLOW}[dry-run]${NC} Would remove legacy path: ${CYAN}${item}${NC}"
    done
    return 0
  fi

  for item in "${found_legacy[@]}"; do
    if [[ -d "$item" ]]; then
      rm -rf "$item"
      msg_success "Removed legacy directory: ${CYAN}${item}${NC}"
    elif [[ -f "$item" ]]; then
      rm -f "$item"
      msg_success "Removed legacy file: ${CYAN}${item}${NC}"
    fi
  done
}

# --- Version check ---
check_for_updates() {
  local latest_version="${VERSION}"
  local version_file="${TARGET_PLUGIN_DIR}/.armature_version"
  if [[ ! -f "$version_file" ]]; then
    version_file="${TARGET_PLUGIN_DIR}/.geppetto_version"
  fi
  if [[ ! -f "$version_file" ]]; then
    version_file="${TARGET_PLUGIN_DIR}/.conductor_version"
  fi

  if [[ -f "$version_file" ]]; then
    local installed_version
    installed_version=$(cat "$version_file" 2>/dev/null | tr -d '[:space:]')

    if [[ "$installed_version" == "$latest_version" ]]; then
      msg_success "Armature plugin is up to date (${CYAN}v${installed_version}${RESET})"
    else
      echo -e "${YELLOW}⚠️  Update available:${RESET} ${DIM}v${installed_version}${RESET} → ${CYAN}v${latest_version}${RESET}"
    fi
  else
    msg_info "Armature plugin installed at ${CYAN}${TARGET_PLUGIN_DIR}${RESET}"
  fi
  echo ""
  echo -e "${DIM}To update to the latest version at any time, run:${RESET}"
  echo -e "${CYAN}git pull && bash install.sh --update${RESET}"
}


# =============================================================================
# Main flow
# =============================================================================

banner

if [[ "${FLAGS_release_notes}" -eq "${FLAGS_TRUE}" ]]; then
  if [[ -f "${SOURCE_CHANGELOG:-}" ]]; then
    section "📝 Release Notes — v${VERSION}"
    echo ""
    awk -v ver="${VERSION}" '
      /^## \[/ { if (found) exit; if (index($0, ver)) found=1 }
      found { print "  " $0 }
    ' "${SOURCE_CHANGELOG}"
    echo ""
  else
    msg_warn "CHANGELOG.md not found."
  fi
  exit 0
fi

if [[ "${FLAGS_update}" -eq "${FLAGS_TRUE}" ]]; then
  FLAGS_force="${FLAGS_TRUE}"

  select_target
  build_target_list

  version_file="${TARGET_PLUGIN_DIR}/.armature_version"
  if [[ ! -f "$version_file" ]]; then
    version_file="${TARGET_PLUGIN_DIR}/.geppetto_version"
  fi
  if [[ ! -f "$version_file" ]]; then
    version_file="${TARGET_PLUGIN_DIR}/.conductor_version"
  fi

  if [[ -f "$version_file" ]]; then
    installed_version=$(cat "$version_file" 2>/dev/null | tr -d '[:space:]')
    if [[ "$installed_version" == "$VERSION" ]]; then
      msg_success "Already up to date (${WHITE}v${VERSION}${NC})"
      exit 0
    fi
    echo -e "  ${DIM}Installed:${NC} ${WHITE}v${installed_version}${NC}  →  ${GREEN}v${VERSION}${NC}"
  else
    msg_info "No existing plugin installation found. Performing fresh install."
  fi
  echo ""
fi

if [[ -z "${INSTALL_TARGET:-}" ]]; then
  select_target
  build_target_list
fi

echo -e "  ${DIM}Target:${NC}      ${WHITE}${TARGET_PLUGIN_DIR}${NC}"

# =============================================================================
# Uninstall
# =============================================================================
if [[ "${FLAGS_uninstall}" -eq "${FLAGS_TRUE}" ]]; then
  section "🗑️  Uninstalling Armature Plugin"
  echo ""

  removed=0
  if [[ -d "${TARGET_PLUGIN_DIR}" ]]; then
    if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
      msg_info "${YELLOW}[dry-run]${NC} Would remove plugin directory: ${CYAN}${TARGET_PLUGIN_DIR}${NC}"
    else
      rm -rf "${TARGET_PLUGIN_DIR}"
      msg_success "Removed plugin directory: ${CYAN}${TARGET_PLUGIN_DIR}${NC}"
    fi
    ((removed++))
  fi

  # Also clean legacy conductor/geppetto plugin, extension, and antigravity directories if present
  migrate_legacy_conductor_plugin
  migrate_to_v0_12_0

  echo ""
  if [[ $removed -eq 0 ]]; then
    msg_info "Nothing to uninstall — no Armature plugin found."
  else
    echo -e "  ${GREEN}🧹 Uninstalled Armature plugin. All clean!${NC}"
  fi
  echo ""
  exit 0
fi

# =============================================================================
# Install
# =============================================================================

validate_sources

if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
  echo -e "  ${YELLOW}👀 DRY RUN MODE — no files will be written${NC}"
fi

# --- Legacy migrations ---
migrate_legacy_conductor_plugin
migrate_from_workflows
migrate_from_hub_skill
migrate_to_v0_11_0
migrate_to_v0_12_0

# --- Assets ---
section "📄 Installing Armature Setup Assets"
echo ""
install_file "${SOURCE_ASSETS_DIR}/workflow_template.md" "${TARGET_ASSETS_DIR}/workflow_template.md"
install_file "${SOURCE_ASSETS_DIR}/adr_template.md" "${TARGET_ASSETS_DIR}/adr_template.md"
install_file "${SOURCE_ASSETS_DIR}/manual_testing_template.md" "${TARGET_ASSETS_DIR}/manual_testing_template.md"

# --- Write version stamps ---
if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
  msg_info "${YELLOW}[dry-run]${NC} Would write version file: ${GREEN}.armature_version${NC}"
else
  mkdir -p "${TARGET_SKILLS_ROOT}/arm-setup"
  echo "$VERSION" > "${TARGET_SKILLS_ROOT}/arm-setup/.armature_version"
  echo "$VERSION" > "${TARGET_PLUGIN_DIR}/.armature_version"
  msg_success "Wrote version stamp: ${GREEN}v${VERSION}${NC}"
fi

# --- Deploy check-update.sh to canonical user cache path ---
install_update_checker() {
  local cache_dir="${HOME}/.cache/armature"
  local target_script="${cache_dir}/check-update.sh"
  local source_script="${SCRIPT_DIR}/check-update.sh"

  if [[ ! -f "${source_script}" ]]; then
    return 0
  fi

  if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
    msg_info "${YELLOW}[dry-run]${NC} Would deploy update checker to ${GREEN}${target_script}${NC} (v${VERSION})"
    return 0
  fi

  mkdir -p "${cache_dir}" 2>/dev/null || true
  sed "s/^INSTALLED_VERSION=.*/INSTALLED_VERSION=\"${VERSION}\"/" "${source_script}" > "${target_script}"
  chmod +x "${target_script}" 2>/dev/null || true
  msg_success "Deployed update checker: ${GREEN}${target_script}${NC} (v${VERSION})"
}
install_update_checker

# --- Manifests & Docs ---
section "📦 Installing Armature Plugin Manifests & Docs"
echo ""
install_file "${SCRIPT_DIR}/plugin.json" "${TARGET_PLUGIN_DIR}/plugin.json"
install_file "${SCRIPT_DIR}/README.md" "${TARGET_PLUGIN_DIR}/README.md"
install_file "${SCRIPT_DIR}/CHANGELOG.md" "${TARGET_PLUGIN_DIR}/CHANGELOG.md"
if [[ -f "${SCRIPT_DIR}/.claude-plugin/marketplace.json" ]]; then
  install_file "${SCRIPT_DIR}/.claude-plugin/marketplace.json" "${TARGET_PLUGIN_DIR}/.claude-plugin/marketplace.json"
fi

# --- Sub-Skills ---
section "🔧 Installing Armature Command Skills"
echo ""
for sub_skill in "${SUB_SKILL_NAMES[@]}"; do
  install_file "${SCRIPT_DIR}/skills/${sub_skill}/SKILL.md" "${TARGET_SKILLS_ROOT}/${sub_skill}/SKILL.md"
done

# --- Rules ---
section "📏 Installing Armature Rules"
echo ""
for rule_file in "${RULE_FILE_NAMES[@]}"; do
  install_file "${SOURCE_RULES_DIR}/${rule_file}" "${TARGET_RULES_ROOT}/${rule_file}"
done
for ref_file in "${REFERENCE_FILE_NAMES[@]}"; do
  install_file "${SOURCE_RULES_DIR}/${ref_file}" "${TARGET_RULES_ROOT}/${ref_file}"
done

# --- Plugin Enablement ---
sync_config_json_plugins

# --- Summary ---
section "Summary"
echo -e "${BOLD}Version:${RESET}     ${CYAN}${VERSION}${RESET}"
echo -e "${BOLD}Source:${RESET}      ${CYAN}${SCRIPT_DIR}${RESET}"
echo -e "${BOLD}Plugin dir:${RESET}  ${CYAN}${TARGET_PLUGIN_DIR}${RESET}"
echo -e "${BOLD}Skills:${RESET}      ${CYAN}${TARGET_SKILLS_ROOT}/arm-*/${RESET}"
echo -e "${BOLD}Rules:${RESET}       ${CYAN}${TARGET_RULES_ROOT}/*.md${RESET}"
echo -e "${BOLD}Files:${RESET}       ${CYAN}${#ALL_TARGET_FILES[@]} total${RESET}"
echo ""

check_for_updates

# --- Optional dependency check ---
if ! command -v sg &>/dev/null; then
  echo -e "${YELLOW}⚠️   ast-grep (sg) not found${RESET}"
  echo -e "   ${DIM}API surface extraction will use regex fallback.${RESET}"
  echo -e "   ${DIM}For higher-quality glossary suggestions, install ast-grep:${RESET}"
  echo -e "   ${CYAN}https://ast-grep.github.io/guide/quick-start.html${RESET}"
  echo ""
fi

if [[ "${FLAGS_dry_run}" -eq "${FLAGS_TRUE}" ]]; then
  echo -e "${YELLOW}${BOLD}══════════════════════════════════════════════════════${RESET}"
  echo -e "${YELLOW}${BOLD}🔍 Dry run complete${RESET}  ${DIM}re-run without --dry_run to apply changes${RESET}"
  echo -e "${YELLOW}${BOLD}══════════════════════════════════════════════════════${RESET}"
else
  echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════════${RESET}"
  echo -e "${GREEN}${BOLD}✅ Armature (OSS) Installer${RESET}  ${DIM}complete${RESET}"
  echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════════${RESET}"
  echo ""
  echo -e "${DIM}💡 If IDE or the web UI is already open, reload the tab (${BOLD}Cmd+R${DIM} / ${BOLD}F5${DIM}) to refresh the slash menu.${RESET}"
fi
echo ""

