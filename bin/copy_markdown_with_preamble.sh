#!/bin/sh

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# OSC 8 hyperlink function
hyperlink() {
    local url="$1"
    local text="${2:-$url}"
    printf '\033]8;;%s\033\\%s\033]8;;\033\\' "$url" "$text"
}

print_status() {
    local emoji="$1"
    local message="$2"
    local color="${3:-$RESET}"
    printf "${color}${emoji} ${message}${RESET}\n"
}

declare FILENAME="$1"

if [ -z "$FILENAME" ]; then
    print_status "❌" "Please provide a filename as an argument" "$RED"
    exit 1
fi

if [ ! -f "$FILENAME" ]; then
    print_status "❌" "File not found: $FILENAME" "$RED"
    exit 1
fi

print_status "📄" "Processing file: ${BOLD}$FILENAME${RESET}" "$CYAN"
 
get_value_from_key() {
  local file="$FILENAME"
  local key="$1"
  awk -v k="$key" '
    BEGIN { FS=": "; OFS=": " }
    {
      if ($1 == k) {
        sub(/^[^:]+: /, ""); # Remove the "key: " portion
        print;
        exit;
      }
    }
  ' "$file"
}

declare subject=$(get_value_from_key "Subject")
declare notion=$(get_value_from_key "Notion-Id")

print_status "📝" "Generating Slack-formatted content..." "$BLUE"

echo "Today's Filecoin-centric monologue: [$subject]($notion), now available on [Notion]($notion), or [on the web/email](https://buttondown.email/dannyob/archive/)"

echo "----\n"

echo "# $subject"
sed '1,/^$/d' $FILENAME

print_status "🤖" "Generating haiku summary..." "$MAGENTA"
llm "Summarise this newsletter in a haiku" < $FILENAME

print_status "✅" "Content formatted for Slack!" "$GREEN"
