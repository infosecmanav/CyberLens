# Wave 1 report — connector framework

Status: complete

The connector layer provides capability manifests, entity routing, concurrency and timeout bounds, feed routing, and explicit success, absence, configuration, quota, authentication, network, parsing, source, and terms outcomes. Missing keys do not stop other sources.

The persisted source registry exposes capabilities, health, required environment-variable names, last checks, errors, and administrator-triggered bounded tests without returning secret values. The Angular source console uses these APIs and exposes the same states.
