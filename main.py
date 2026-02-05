"""
DJ Toggle Experiment Populator

Populates three experiments (lead, bass, drums) with simulated user votes.
Each experiment has a clear winner with close but distinguishable results.

Winners (higher conversion rates):
  - Lead:  banjo         (~38% conversion)
  - Bass:  trance        (~38% conversion)
  - Drums: fourOnTheFloor (~38% conversion)

Runner-ups (~28-30% conversion):
  - Lead:  techno, epiano, organ, original
  - Bass:  original, tuba, strings
  - Drums: original, syncopated, casio

Excluded from experiments (0% conversion if somehow evaluated):
  - Lead:  silence
  - Bass:  silence
  - Drums: basicTick
"""

import os

import ldclient
from ldclient import Context
from ldclient.config import Config
from dotenv import load_dotenv
import random
import time
import uuid

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

SDK_KEY = os.environ.get("SDK_KEY")
NUMBER_OF_ITERATIONS = 207
METRIC_NAME = "vote"

# Event flushing configuration
FLUSH_INTERVAL = 10      # Flush events every N iterations

# Timing configuration: scatter results over ~3 minutes with non-uniform delays
TARGET_DURATION_SECONDS = 180  # 3 minutes total
# Average sleep per iteration to hit ~3 min: 180s / 207 iterations ≈ 0.87s
# We'll use exponential distribution for non-uniform, "bursty" timing

# Experiment flag keys
LEAD_FLAG = "leadArrangement"
BASS_FLAG = "bassArrangement"
DRUMS_FLAG = "drumArrangement"

# =============================================================================
# CONVERSION RATES
#
# Winners get ~38% conversion rate
# Runner-ups get ~28-30% conversion rate
# Excluded variations get 0% (silence/basicTick)
# =============================================================================

LEAD_CONVERSION_RATES = {
    "banjo": 38,      # WINNER - Hell yeah brother!
    "techno": 29,
    "epiano": 28,
    "organ": 27,
    "original": 30,
    "silence": 0,     # EXCLUDED - should not be in experiment
}

BASS_CONVERSION_RATES = {
    "trance": 38,     # WINNER - Driving sawtooth bass
    "original": 29,
    "tuba": 27,
    "strings": 28,
    "silence": 0,     # EXCLUDED - should not be in experiment
}

DRUMS_CONVERSION_RATES = {
    "fourOnTheFloor": 38,  # WINNER - Classic dance floor kick
    "original": 29,
    "syncopated": 28,
    "casio": 27,
    "basicTick": 0,        # EXCLUDED - should not be in experiment
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_random_context():
    """Create a new random context for each evaluation."""
    return Context.builder(str(uuid.uuid4())).kind("request").build()


def should_convert(conversion_rate: int) -> bool:
    """Determine if this user should 'convert' based on the conversion rate."""
    return random.randint(1, 100) <= conversion_rate


def get_conversion_rate(variation: str, rates: dict) -> int:
    """Get conversion rate for a variation, defaulting to 0 if unknown."""
    return rates.get(variation, 0)


def random_sleep():
    """
    Generate a non-uniform sleep duration using exponential distribution.
    This creates "bursty" traffic - some iterations come quickly, others have longer gaps.
    Average sleep is ~0.87s to spread 207 iterations over ~3 minutes.
    """
    # Exponential distribution with mean of 0.87 seconds
    # Capped at 5 seconds max to avoid any single very long pause
    sleep_time = min(random.expovariate(1 / 0.87), 5.0)
    return sleep_time


# =============================================================================
# MAIN EXPERIMENT POPULATION LOGIC
# =============================================================================

def populate_experiments():
    """
    Loop through 207 iterations, evaluating all three experiments
    and tracking 'vote' conversions based on configured rates.
    """

    # Tracking stats for summary
    stats = {
        "lead": {},
        "bass": {},
        "drums": {},
    }

    print("=" * 60)
    print("DJ Toggle Experiment Populator")
    print("=" * 60)
    print(f"Running {NUMBER_OF_ITERATIONS} iterations over ~3 minutes...")
    print(f"Metric: {METRIC_NAME}")
    print()
    print("Expected winners (higher conversion rates ~38%):")
    print("  - Lead:  banjo")
    print("  - Bass:  trance")
    print("  - Drums: fourOnTheFloor")
    print()
    print("Excluded from experiments (0% conversion):")
    print("  - Lead:  silence")
    print("  - Bass:  silence")
    print("  - Drums: basicTick")
    print("=" * 60)
    print()

    client = ldclient.get()

    for i in range(NUMBER_OF_ITERATIONS):
        # Create a FRESH context for each iteration
        context = create_random_context()

        # ----- LEAD EXPERIMENT -----
        lead_variation = client.variation(LEAD_FLAG, context, "original")
        lead_rate = get_conversion_rate(lead_variation, LEAD_CONVERSION_RATES)

        if lead_variation not in stats["lead"]:
            stats["lead"][lead_variation] = {"total": 0, "converted": 0}
        stats["lead"][lead_variation]["total"] += 1

        if should_convert(lead_rate):
            client.track(METRIC_NAME, context)
            stats["lead"][lead_variation]["converted"] += 1

        # ----- BASS EXPERIMENT -----
        bass_variation = client.variation(BASS_FLAG, context, "original")
        bass_rate = get_conversion_rate(bass_variation, BASS_CONVERSION_RATES)

        if bass_variation not in stats["bass"]:
            stats["bass"][bass_variation] = {"total": 0, "converted": 0}
        stats["bass"][bass_variation]["total"] += 1

        if should_convert(bass_rate):
            client.track(METRIC_NAME, context)
            stats["bass"][bass_variation]["converted"] += 1

        # ----- DRUMS EXPERIMENT -----
        drums_variation = client.variation(DRUMS_FLAG, context, "original")
        drums_rate = get_conversion_rate(drums_variation, DRUMS_CONVERSION_RATES)

        if drums_variation not in stats["drums"]:
            stats["drums"][drums_variation] = {"total": 0, "converted": 0}
        stats["drums"][drums_variation]["total"] += 1

        if should_convert(drums_rate):
            client.track(METRIC_NAME, context)
            stats["drums"][drums_variation]["converted"] += 1

        # Flush events periodically to avoid overloading the SDK's event queue
        if (i + 1) % FLUSH_INTERVAL == 0:
            client.flush()

        # Progress output every 25 iterations
        if (i + 1) % 25 == 0 or (i + 1) == NUMBER_OF_ITERATIONS:
            print(f"Progress: {i + 1}/{NUMBER_OF_ITERATIONS}")

        # Non-uniform sleep to scatter results over ~3 minutes
        sleep_duration = random_sleep()
        time.sleep(sleep_duration)

    print()
    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    # Final flush to ensure all events are sent
    print("Flushing remaining events...")
    client.flush()
    time.sleep(1)  # Give time for final flush to complete

    for experiment_name, variations in stats.items():
        print(f"\n{experiment_name.upper()} EXPERIMENT:")
        print("-" * 40)
        for variation, data in sorted(variations.items(), key=lambda x: -x[1]["converted"]):
            total = data["total"]
            converted = data["converted"]
            rate = (converted / total * 100) if total > 0 else 0
            winner_marker = ""
            if experiment_name == "lead" and variation == "banjo":
                winner_marker = " <-- WINNER"
            elif experiment_name == "bass" and variation == "trance":
                winner_marker = " <-- WINNER"
            elif experiment_name == "drums" and variation == "fourOnTheFloor":
                winner_marker = " <-- WINNER"
            print(f"  {variation:20} | {converted:3}/{total:3} ({rate:5.1f}%){winner_marker}")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Validate SDK key is set
    if not SDK_KEY:
        print("ERROR: SDK_KEY environment variable is not set.")
        print("Please set it in your .env file or export it as an environment variable.")
        exit(1)

    # Initialize the LaunchDarkly SDK
    ldclient.set_config(Config(SDK_KEY))

    if ldclient.get().is_initialized():
        print("LaunchDarkly SDK initialized successfully!\n")
        populate_experiments()
    else:
        print("ERROR: LaunchDarkly SDK failed to initialize.")
        print("Check your SDK key and network connection.")

    # Always close the client properly
    ldclient.get().close()
    print("\nDone! LaunchDarkly client closed.")
