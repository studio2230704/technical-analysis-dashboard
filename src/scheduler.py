"""Scheduler for hourly alert checks."""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

import schedule
from dotenv import load_dotenv

# Add src directory to path for imports
src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

from alert_checker import run_alert_check, send_alerts


def get_watchlist_path() -> Path:
    """Get watchlist path from env or default."""
    env_path = os.getenv("WATCHLIST_PATH")
    if env_path:
        return Path(env_path)

    # Default: watchlist.csv in project root
    return Path(__file__).parent.parent / "watchlist.csv"


def job():
    """Run the alert check job."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*50}")
    print(f"[{now}] Starting alert check...")
    print(f"{'='*50}")

    watchlist_path = get_watchlist_path()

    try:
        alerts = run_alert_check(watchlist_path)

        if alerts:
            print(f"\n🔔 {len(alerts)} alert(s) found!")
            send_alerts(alerts)
        else:
            print("\n✓ No alerts triggered")

    except Exception as e:
        print(f"\n✗ Error during alert check: {e}")

    print(f"\nNext check in 1 hour...")


def main():
    """Main entry point for scheduler."""
    # Load environment variables
    load_dotenv()

    # Verify LINE token is configured
    if not os.getenv("LINE_NOTIFY_TOKEN"):
        print("⚠️  Warning: LINE_NOTIFY_TOKEN not set. Alerts will not be sent.")
        print("   Set it in .env file or as environment variable.")

    print("📊 Stock Alert Scheduler Started")
    print(f"   Watchlist: {get_watchlist_path()}")
    print("   Frequency: Every hour")
    print("\n   Press Ctrl+C to stop\n")

    # Run immediately on start
    job()

    # Schedule hourly checks
    schedule.every().hour.do(job)

    # Keep running
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\n\nScheduler stopped.")


if __name__ == "__main__":
    main()
