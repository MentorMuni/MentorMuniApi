#!/bin/bash

###############################################################################
# MentorMuni Database Schema Export Script
# 
# Purpose: Export database schema, data, and create backups
# Usage: ./export-database-schema.sh [options]
# 
# Options:
#   --full              Full backup (schema + data)
#   --schema-only       Schema only (no data)
#   --data-only         Data only (no schema)
#   --know-me-only      Know Me tables only
#   --compressed        Gzip compress output
#   --output FILE       Custom output file
#   --help              Show this help message
###############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DB_HOST="${DB_HOST:-crossover.proxy.rlwy.net}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-railway}"
DB_PORT="${DB_PORT:-52225}"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Default options
BACKUP_TYPE="full"
COMPRESS=false
OUTPUT_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            BACKUP_TYPE="full"
            shift
            ;;
        --schema-only)
            BACKUP_TYPE="schema"
            shift
            ;;
        --data-only)
            BACKUP_TYPE="data"
            shift
            ;;
        --know-me-only)
            BACKUP_TYPE="know-me"
            shift
            ;;
        --compressed)
            COMPRESS=true
            shift
            ;;
        --output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        --help)
            head -n 20 "$0" | tail -n +2 | sed 's/^# //'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo -e "${GREEN}=== MentorMuni Database Export ===${NC}"
echo "Host: $DB_HOST"
echo "Database: $DB_NAME"
echo "Type: $BACKUP_TYPE"
echo "Time: $TIMESTAMP"
echo ""

# Function to export based on type
export_database() {
    local output_file="$1"
    local opts=""
    
    case $BACKUP_TYPE in
        full)
            echo -e "${YELLOW}Exporting FULL backup (schema + data)...${NC}"
            opts=""
            ;;
        schema)
            echo -e "${YELLOW}Exporting SCHEMA ONLY...${NC}"
            opts="--schema-only"
            ;;
        data)
            echo -e "${YELLOW}Exporting DATA ONLY...${NC}"
            opts="--data-only"
            ;;
        know-me)
            echo -e "${YELLOW}Exporting KNOW ME tables only...${NC}"
            opts="--data-only -t private_student_checkins -t private_student_responses -t private_student_insights -t private_student_progress"
            ;;
    esac
    
    # Execute pg_dump
    if [ -z "$DB_PASSWORD" ]; then
        pg_dump -h "$DB_HOST" -U "$DB_USER" -p "$DB_PORT" -d "$DB_NAME" $opts > "$output_file"
    else
        PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -U "$DB_USER" -p "$DB_PORT" -d "$DB_NAME" $opts > "$output_file"
    fi
}

# Determine output file
if [ -z "$OUTPUT_FILE" ]; then
    case $BACKUP_TYPE in
        full)
            OUTPUT_FILE="$BACKUP_DIR/full_backup_${TIMESTAMP}"
            ;;
        schema)
            OUTPUT_FILE="$BACKUP_DIR/schema_${TIMESTAMP}"
            ;;
        data)
            OUTPUT_FILE="$BACKUP_DIR/data_${TIMESTAMP}"
            ;;
        know-me)
            OUTPUT_FILE="$BACKUP_DIR/know_me_backup_${TIMESTAMP}"
            ;;
    esac
fi

# Add compression extension if needed
if [ "$COMPRESS" = true ]; then
    OUTPUT_FILE="${OUTPUT_FILE}.sql.gz"
    export_database "/tmp/temp_export.sql"
    echo -e "${YELLOW}Compressing...${NC}"
    gzip -c "/tmp/temp_export.sql" > "$OUTPUT_FILE"
    rm "/tmp/temp_export.sql"
else
    OUTPUT_FILE="${OUTPUT_FILE}.sql"
    export_database "$OUTPUT_FILE"
fi

# Get file size
FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)

echo -e "${GREEN}✓ Export completed successfully!${NC}"
echo ""
echo "Output File: $OUTPUT_FILE"
echo "File Size: $FILE_SIZE"
echo ""

# Show restore instructions
echo -e "${YELLOW}To restore this backup:${NC}"
if [[ "$OUTPUT_FILE" == *.gz ]]; then
    echo "gunzip -c $OUTPUT_FILE | psql -h $DB_HOST -U $DB_USER -d $DB_NAME"
else
    echo "psql -h $DB_HOST -U $DB_USER -d $DB_NAME < $OUTPUT_FILE"
fi

# Auto-cleanup old backups (keep only 7 days)
echo ""
echo -e "${YELLOW}Cleaning up old backups (older than 7 days)...${NC}"
find "$BACKUP_DIR" -name "*.sql*" -mtime +7 -exec rm {} \;
echo -e "${GREEN}✓ Cleanup complete${NC}"
