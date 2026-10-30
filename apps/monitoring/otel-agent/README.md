# Older OTel agent

`manifest.yaml` is retained as reference. The monitoring Kustomization does not include it.
Pod logs are collected by `../fluent-bit/` instead. Do not deploy both collectors for the same files.
