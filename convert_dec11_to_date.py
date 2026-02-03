
def convert():
    input_file = "dixon_trades_dec11_to_date.txt"
    output_file = "/Users/poojapatel/.gemini/antigravity/brain/5531471d-ed0b-4c39-8596-a0fc3142c2a4/dixon_trades_dec11_to_date_table.md"
    
    with open(input_file, 'r') as f:
        lines = f.readlines()
    
    with open(output_file, 'w') as f:
        f.write("# DIXON Trades - Dec 11 2025 to Jan 31 2026\n\n")
        
        table_started = False
        for line in lines:
            if "ID" in line and "Time" in line and "|" in line:
                f.write(line)
                f.write("|---|---|---|---|---|---|\n")
                table_started = True
                continue
            
            if table_started:
                if "--- SUMMARY ---" in line:
                    break
                if line.strip() == "":
                    continue
                f.write(line)
        
        f.write("\n## Summary\n")
        for line in lines:
            if "Total Trades:" in line or "Total Cumulative PnL:" in line:
                f.write(f"- {line}")

if __name__ == "__main__":
    convert()
