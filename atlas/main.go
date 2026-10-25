// Aodı-NexusZero — atlas: sovereign P2P mesh discovery daemon (stdlib only).
//
// Responsibilities (Go owns discovery, Python owns planning):
//
//	GET  /atlas/state   this device self-state (name, tags, ollama, load, battery)
//	GET  /atlas/nodes   self + all known peers with liveness
//	POST /atlas/peers   {"peers":["http://ip:9301", ...]} seed/replace peer set
//	GET  /atlas/health  version + uptime + counters
//
// Heartbeats run concurrently (one goroutine per peer, bounded); a peer is
// DOWN after 3 consecutive misses. Peer state is read through an RWMutex.
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	version      = "1.0.0"
	defaultAddr  = ":9301"
	missesToDown = 3
	httpTimeout  = 3 * time.Second
)

type Self struct {
	Name      string   `json:"name"`
	Tags      []string `json:"tags"`
	OllamaURL string   `json:"ollama_url"`
}

type peer struct {
	URL       string   `json:"url"`
	Up        bool     `json:"up"`
	Misses    int      `json:"-"`
	Load      float64  `json:"load"`
	Battery   *int     `json:"battery"`
	Latency   int      `json:"latency_ms"`
	Tags      []string `json:"tags"`
	OllamaURL string   `json:"ollama_url"`
	Seen      string   `json:"last_seen"`
}

var (
	mu      sync.RWMutex
	self    Self
	peers   = map[string]*peer{}
	started = time.Now()
	hbEvery = 10 * time.Second
)

func getenv(k, d string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return d
}

func tagsCSV(s string) []string {
	if s == "" {
		return []string{"lite"}
	}
	parts := strings.Split(s, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		if p = strings.TrimSpace(p); p != "" {
			out = append(out, p)
		}
	}
	return out
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func stateHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, 200, map[string]any{
		"name": self.Name, "tags": self.Tags, "ollama_url": self.OllamaURL,
		"load": 0.0, "battery": nil, "role": "atlas",
	})
}

func nodesHandler(w http.ResponseWriter, r *http.Request) {
	mu.RLock()
	defer mu.RUnlock()
	list := make([]map[string]any, 0, len(peers)+1)
	for _, p := range peers {
		list = append(list, map[string]any{
			"name": nameOf(p.URL), "url": p.URL, "up": p.Up,
			"load": p.Load, "battery": p.Battery, "latency_ms": p.Latency,
			"tags": p.Tags, "ollama_url": p.OllamaURL, "last_seen": p.Seen,
		})
	}
	writeJSON(w, 200, map[string]any{"nodes": list})
}

func nameOf(url string) string {
	s := strings.TrimPrefix(strings.TrimPrefix(url, "https://"), "http://")
	if i := strings.Index(s, ":"); i > 0 {
		s = s[:i]
	}
	return "peer-" + s
}

func peersHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodPost {
		body, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
		if err != nil {
			writeJSON(w, 400, map[string]string{"error": "read failed"})
			return
		}
		var in struct {
			Peers []string `json:"peers"`
		}
		if err := json.Unmarshal(body, &in); err != nil {
			writeJSON(w, 400, map[string]string{"error": "bad json"})
			return
		}
		mu.Lock()
		for _, u := range in.Peers {
			u = strings.TrimSpace(u)
			if u == "" || !strings.HasPrefix(u, "http") {
				continue
			}
			if _, ok := peers[u]; !ok {
				peers[u] = &peer{URL: u}
			}
		}
		mu.Unlock()
		writeJSON(w, 200, map[string]any{"ok": true, "count": len(peers)})
		return
	}
	mu.RLock()
	defer mu.RUnlock()
	urls := make([]string, 0, len(peers))
	for u := range peers {
		urls = append(urls, u)
	}
	writeJSON(w, 200, map[string]any{"peers": urls})
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	mu.RLock()
	up := 0
	for _, p := range peers {
		if p.Up {
			up++
		}
	}
	mu.RUnlock()
	writeJSON(w, 200, map[string]any{
		"service": "nexuszero.atlas", "version": version,
		"uptime_seconds": int(time.Since(started).Seconds()),
		"peers_known":    len(peers), "peers_up": up,
		"heartbeat_s": int(hbEvery.Seconds()),
	})
}

func heartbeatOnce() {
	mu.RLock()
	urls := make([]string, 0, len(peers))
	for u := range peers {
		urls = append(urls, u)
	}
	mu.RUnlock()

	var wg sync.WaitGroup
	client := &http.Client{Timeout: httpTimeout}
	for _, u := range urls {
		wg.Add(1)
		go func(raw string) {
			defer wg.Done()
			t0 := time.Now()
			resp, err := client.Get(strings.TrimSuffix(raw, "/") + "/atlas/state")
			mu.Lock()
			p := peers[raw]
			if p == nil {
				mu.Unlock()
				return
			}
			if err != nil || resp.StatusCode != http.StatusOK {
				if err == nil {
					resp.Body.Close()
				}
				p.Misses++
				if p.Misses >= missesToDown {
					p.Up = false
				}
				mu.Unlock()
				return
			}
			var st map[string]any
			body, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
			resp.Body.Close()
			_ = json.Unmarshal(body, &st)
			p.Up, p.Misses = true, 0
			p.Latency = int(time.Since(t0).Milliseconds())
			if l, ok := st["load"].(float64); ok {
				p.Load = l
			}
			if b, ok := st["battery"].(float64); ok {
				bi := int(b)
				p.Battery = &bi
			} else {
				p.Battery = nil
			}
			if t, ok := st["tags"].([]any); ok {
				tags := make([]string, 0, len(t))
				for _, x := range t {
					if s, o := x.(string); o {
						tags = append(tags, s)
					}
				}
				p.Tags = tags
			}
			if ou, ok := st["ollama_url"].(string); ok {
				p.OllamaURL = ou
			}
			p.Seen = time.Now().UTC().Format(time.RFC3339)
			mu.Unlock()
		}(u)
	}
	wg.Wait()
}

func heartbeatLoop() {
	for {
		heartbeatOnce()
		time.Sleep(hbEvery)
	}
}

func main() {
	self = Self{
		Name:      getenv("NZX_NAME", hostname()),
		Tags:      tagsCSV(getenv("NZX_TAGS", "lite,gpu")),
		OllamaURL: getenv("NZX_OLLAMA", "http://127.0.0.1:11434"),
	}
	if so := os.Getenv("NZX_ATLAS_HEARTBEAT_S"); so != "" {
		if n, err := strconv.Atoi(so); err == nil && n > 0 && n <= 300 {
			hbEvery = time.Duration(n) * time.Second
		}
	}
	// Seed peers from env (comma separated) after startup.
	if seeds := os.Getenv("NZX_PEERS"); seeds != "" {
		var list []string
		for _, s := range strings.Split(seeds, ",") {
			if s = strings.TrimSpace(s); s != "" {
				list = append(list, s)
			}
		}
		go func() {
			time.Sleep(500 * time.Millisecond)
			body, _ := json.Marshal(map[string]any{"peers": list})
			req, err := http.NewRequest(http.MethodPost,
				"http://127.0.0.1"+getenv("NZX_ADDR", defaultAddr)+"/atlas/peers",
				bytes.NewReader(body))
			if err == nil {
				client := &http.Client{Timeout: 2 * time.Second}
				_, _ = client.Do(req)
			}
		}()
	}
	go heartbeatLoop()

	mux := http.NewServeMux()
	mux.HandleFunc("/atlas/state", stateHandler)
	mux.HandleFunc("/atlas/nodes", nodesHandler)
	mux.HandleFunc("/atlas/peers", peersHandler)
	mux.HandleFunc("/atlas/health", healthHandler)

	addr := getenv("NZX_ADDR", defaultAddr)
	srv := &http.Server{Addr: addr, Handler: mux,
		ReadHeaderTimeout: 5 * time.Second,
		WriteTimeout:      10 * time.Second}
	fmt.Println("Aodı-NexusZero atlas v"+version, "listening on", addr,
		"name:", self.Name, "ollama:", self.OllamaURL)
	_ = srv.ListenAndServe()
}

func hostname() string {
	h, err := os.Hostname()
	if err != nil {
		return "atlas-local"
	}
	return h
}
