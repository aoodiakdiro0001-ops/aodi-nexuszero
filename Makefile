.PHONY: atlas core tests clean

atlas:              ## build atlas P2P daemon
	cd atlas && gofmt -w . && go vet ./... && go build -o ../bin/nzx-atlas .

core:               ## hivemind core API + dashboard on :9302
	python3 core/server.py --port 9302

tests:              ## offline test battery
	python3 tests/test_nexuszero.py -v
	node --check relay/relay.js

demo-scan:          ## sentinel live audit of the planted fixture
	python3 core/cli.py scan examples/vuln_fixture.py

demo-run:           ## sharded distributed goal
	python3 core/cli.py run "design the API contract for a chat ingest service, then implement a batching pipeline"
