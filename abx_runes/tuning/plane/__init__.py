"""
Tuning plane router (bundle builder).

This layer sits above TuningIR:
- computes drift/degraded
- clamps policy via Risk Governor
- can emit a Do-Nothing bundle (still hashed + provenance locked)
"""

