#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"
ICON_BASE="${HOME}/.local/share/icons/hicolor"

if [[ "${1:-}" == "--uninstall" || "${1:-}" == "-u" ]]; then
    echo "Uklanjanje Čelix aplikacije..."
    rm -f "${BIN_DIR}/celix"
    rm -f "${APP_DIR}/celix.desktop" "${APP_DIR}/celik-linux.desktop"
    for size in 16x16 32x32 48x48 256x256; do
        rm -f "${ICON_BASE}/${size}/apps/celix.png"
    done
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "${APP_DIR}" || true
    echo "Čelix je uspešno uklonjen."
    exit 0
fi

echo "Instalacija Čelix aplikacije za korisnika ${USER}..."

mkdir -p "${BIN_DIR}" "${APP_DIR}"

# Instalacija izvršnog fajla
if [[ -f "${SCRIPT_DIR}/celix" ]]; then
    install -m 755 "${SCRIPT_DIR}/celix" "${BIN_DIR}/celix"
else
    echo "Greška: Izvršni fajl '${SCRIPT_DIR}/celix' nije pronađen." >&2
    exit 1
fi

# Instalacija ikonica u više rezolucija
declare -A ICONS=(
    ["16x16"]="celik_1_16x16x32.png"
    ["32x32"]="celik_2_32x32x32.png"
    ["48x48"]="celik_3_48x48x32.png"
    ["256x256"]="celik_4_256x256x32.png"
)

for size in "${!ICONS[@]}"; do
    src="${SCRIPT_DIR}/assets/${ICONS[$size]}"
    if [[ -f "${src}" ]]; then
        mkdir -p "${ICON_BASE}/${size}/apps"
        install -m 644 "${src}" "${ICON_BASE}/${size}/apps/celix.png"
    fi
done

# Instalacija .desktop fajla (sa punom putanjom do ~/.local/bin/celix radi kompatibilnosti sa svim DE)
sed "s|^Exec=celix$|Exec=${BIN_DIR}/celix|" "${SCRIPT_DIR}/celik-linux.desktop" > "${APP_DIR}/celix.desktop"
chmod 644 "${APP_DIR}/celix.desktop"

# Osvežavanje baze aplikacija i ikonica ako su alati dostupni
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "${APP_DIR}" || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t "${ICON_BASE}" >/dev/null 2>&1 || true

echo "Instalacija je završena!"
echo "  - Izvršni fajl: ${BIN_DIR}/celix"
echo "  - Desktop prečica: ${APP_DIR}/celix.desktop"
echo "Za uklanjanje pokrenite: ./install.sh --uninstall"
