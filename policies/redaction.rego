package privypress

default allow := false

min_confidence := 0.85
required_coverage := 1.0

allow {
  input.stats.coverage_estimate >= required_coverage
  not low_conf
}

low_conf {
  some i
  input.detections[i].action == "redact"
  input.detections[i].confidence < min_confidence
}

deny_reason[r] {
  low_conf
  r := "Low-confidence redactions present"
}

deny_reason[r] {
  input.stats.coverage_estimate < required_coverage
  r := "Coverage below requirement"
}
