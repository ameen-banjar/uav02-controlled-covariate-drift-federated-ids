"""
Run the unmodified ISOT extractor on one pcap sub-file.

Usage: extract_one.py EXTRACTOR_DIR IN.pcap OUT_PREFIX
Writes OUT_PREFIX.csv (10-packet mean rows), exactly as
Feature_extraction.pcap_evaluation() does in the original driver.
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")
extractor_dir, pcap, out_prefix = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, extractor_dir)

from Feature_extraction import Feature_extraction  # noqa: E402

fe = Feature_extraction()
fe.pcap_evaluation(pcap, out_prefix)
if not os.path.exists(out_prefix + ".csv"):
    sys.exit("extractor wrote no CSV")
