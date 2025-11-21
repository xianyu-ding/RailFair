#!/usr/bin/env python3
"""
Segmented Collection Runner
Splits large date ranges into smaller chunks and runs them sequentially
"""
import sys
import subprocess
import time
import random
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple

def split_date_range(start_date: str, end_date: str, chunk_days: int = 14) -> List[Tuple[str, str]]:
    """Split a date range into smaller chunks"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    chunks = []
    current = start
    
    while current < end:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end)
        chunks.append((
            current.strftime('%Y-%m-%d'),
            chunk_end.strftime('%Y-%m-%d')
        ))
        current = chunk_end + timedelta(days=1)
    
    return chunks


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run_segmented.py <config_file> [chunk_days] [phase_name]")
        print("  config_file: Path to YAML config (e.g., configs/hsp_config_phase1.yaml)")
        print("  chunk_days: Days per chunk (default: 14)")
        print("  phase_name: Phase name for logging (default: from config)")
        sys.exit(1)
    
    config_file = sys.argv[1]
    chunk_days = int(sys.argv[2]) if len(sys.argv) > 2 else 14
    phase_name = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Load config
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    start_date = config['data_collection']['from_date']
    end_date = config['data_collection']['to_date']
    
    if not phase_name:
        phase_name = config.get('phase', 'Phase 1')
    
    print("=" * 70)
    print("  Segmented HSP Data Collection")
    print("=" * 70)
    print(f"\nConfig: {config_file}")
    print(f"Phase: {phase_name}")
    print(f"Chunk size: {chunk_days} days")
    print(f"Original date range: {start_date} to {end_date}\n")
    
    # Split into chunks
    chunks = split_date_range(start_date, end_date, chunk_days)
    total_chunks = len(chunks)
    
    print(f"Split into {total_chunks} chunks:\n")
    for i, (from_date, to_date) in enumerate(chunks, 1):
        days = (datetime.strptime(to_date, '%Y-%m-%d') - 
                datetime.strptime(from_date, '%Y-%m-%d')).days + 1
        print(f"  Chunk {i}/{total_chunks}: {from_date} to {to_date} ({days} days)")
    
    print("\n" + "=" * 70)
    response = input("Continue with segmented collection? (y/n): ")
    if response.lower() != 'y':
        print("Aborted.")
        sys.exit(0)
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Run each chunk sequentially
    for chunk_num, (from_date, to_date) in enumerate(chunks, 1):
        log_file = log_dir / f"phase1_chunk{chunk_num}.log"
        
        print("\n" + "=" * 70)
        print(f"  Starting Chunk {chunk_num}/{total_chunks}: {from_date} to {to_date}")
        print("=" * 70)
        print(f"Log file: {log_file}\n")
        
        # Build command
        cmd = [
            sys.executable,
            "fetch_hsp_batch.py",
            config_file,
            "--phase", f"{phase_name} - Chunk {chunk_num}",
            "--date-from", from_date,
            "--date-to", to_date
        ]
        
        # Run chunk
        start_time = time.time()
        try:
            with open(log_file, 'w') as log_f:
                result = subprocess.run(
                    cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    text=True
                )
            
            elapsed = time.time() - start_time
            
            if result.returncode == 0:
                print(f"✅ Chunk {chunk_num} completed successfully ({elapsed:.1f}s)")
            else:
                print(f"❌ Chunk {chunk_num} failed with exit code {result.returncode}")
                print(f"   Check log: {log_file}")
                # Continue with next chunk even if this one failed
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error running chunk {chunk_num}: {e}")
            continue
        
        # Random delay between chunks (30-90 seconds) to prevent rate limiting
        if chunk_num < total_chunks:
            delay = random.uniform(30, 90)
            print(f"⏸️  Waiting {delay:.1f}s before next chunk (random delay)...")
            time.sleep(delay)
    
    print("\n" + "=" * 70)
    print("  All chunks completed!")
    print("=" * 70)
    print(f"\nLog files in {log_dir}:")
    for log_file in sorted(log_dir.glob("phase1_chunk*.log")):
        size = log_file.stat().st_size / 1024  # KB
        print(f"  {log_file.name} ({size:.1f} KB)")


if __name__ == '__main__':
    main()

