```
   ╔╦╗ ╦ ╦ ╔╦╗ ╔═╗ ╔═╗ ╦ ╔╗╔    ╔═╗ ╦═╗ ╦ ╦ ╔═╗ ╦ ╦ ╦  ╦ ╔═╗ ╦ ╦ ╔═╗
   ║║║ ║ ║  ║  ╠═╣ ║ ║ ║ ║║║    ╠═╣ ╠╦╝ ╚╦╝ ╠═╣ ║║║ ║  ║ ╠═╣ ╚╦╝ ╠═╣
   ╩ ╩ ╚═╝  ╩  ╩ ╩ ╚═╬ ╩ ╝╚╝    ╩ ╩ ╩╚═  ╩  ╩ ╩ ╚╩╝ ╩ ╚╝ ╩ ╩  ╩  ╩ ╩

   applied machine learning and software engineer · jakarta, indonesia
   computer vision · agentic ai · real time speech · full stack
```

Nearly four years of shipping models and the products around them. I tend to own the whole line:
the evaluation that says whether a model is actually good, the model itself, the backend it runs in,
the interface someone uses it through, and the pager when it breaks at 2am. Most of that has been in
distributed, English first teams across the United States and Singapore.

Most of my code lives in private and organization repositories, so the contribution graph on this
page is a poor summary of the work. What follows is the readable version.

### ▍ Currently

```
   now          ai/ml engineer at boon ai, vision over engineering drawings
   building     marrow, open source memory and coordination for ai agents
   co-founded   workinsights.online, used by 150+ company accounts
   before       fx ops tooling in singapore, edtech, llm evaluation lead
   open to      part time senior engineering work, remote
```

### ▍ Work that is not in the graph

The private and organization side, described by what it does and what it changed.

| Work | |
|:--|:--|
| **Open vocabulary symbol takeoff** | Finds and counts symbols on engineering drawings that the system has never been trained on, from a single example the user points at. No per symbol training, which is the part that normally makes this impractical at customer scale. |
| **Electrical takeoff** | Production computer vision for branch circuit inference across dense plan sets, combining object detection, OCR and schedule reasoning with geometric algorithms and GPU served models. Includes the failure analysis workflow for open set generalization, which is where most of the real accuracy comes from. |
| **Voice agents** | A production agent that phones truck drivers, captures ETA and delivery status, and turns a live phone call into structured operational data. |
| **Clinical speech platform** | Real time transcription with speaker separation, live context for the clinician, and generated SOAP, DAP, BIRP and GIRP notes, wired into Google Meet and existing practice software. Clinicians reported charting time down by up to 10x. Co-founded and led the engineering team. |
| **Workforce analytics SaaS** | Multi tenant product with 150+ registered company accounts, taken end to end: a Windows agent in C#, a macOS agent in Swift, a Next.js dashboard, a React Native app, and a Node and Postgres backend covering ingestion, screenshot processing, billing, background workers, tenant isolation and row level security. Co-founded, and I still run it. |
| **Road damage mapping** | A 27 class detection system over Indonesian road imagery at over 80% reported accuracy, with the mapping product built on top. Spatial queries went from more than 30 seconds to under one second across 50,000 records. |
| **Financial operations platform** | Daily transaction forecasting, balance tracking and fund scheduling for FX operations at a Singapore remittance company, plus an assistant for navigating internal company data. |
| **LLM evaluation at scale** | Promoted to lead six trainers evaluating model output on physics simulation tasks for a large generative AI client, and built the internal tool the team coordinated and tracked quality through. |

### ▍ Marrow

[github.com/aryawidjaja/marrow](https://github.com/aryawidjaja/marrow) · Rust · AGPL-3.0 · [marrow.works](https://www.marrow.works/)

The public one. Coding agents forget everything between sessions, and the usual fix is to write the
whole project into one file the agent re-reads every turn. That works until the project knows more
than fits. Marrow retrieves instead of loading: ask a question, get back the memories that answer it
plus the ones linked to those, out of however many thousand exist. It speaks MCP, so Claude Code,
Cursor and Codex all read and write the same brain.

```
   claude code        cursor           codex         any mcp client
        │               │                │                 │
        └───────────────┴────────┬───────┴─────────────────┘
                                 │  model context protocol
                         ┌───────┴────────┐
                         │     marrow     │   rust · runs on your machine
                         └───────┬────────┘
             ┌───────────────────┼───────────────────┐
             │                   │                   │
      ranked recall         file claims          hash chained
     across projects     across live agents        audit log
```

It also detects when the code a memory describes has changed underneath it, coordinates several
agents so they stop editing the same file, and keeps an append only, hash chained record of what
each one did.

I benchmarked it rather than asserting it. Same repo, same task, 75 runs, graded by running the code
instead of reading it. At 1,000 project facts it holds context flat while a single context file
climbs from 21k to 51k tokens per turn, which works out to 2.1x less context per turn (p = 0.002)
and $0.50 a task instead of $0.90. Below roughly a hundred facts it loses, and the README says so
out loud, because a benchmark you only publish when it flatters you is not a benchmark.

### ▍ Stack

```
   languages    python · typescript · rust · ruby · c# · swift · sql · c++
   ml           pytorch · tensorflow · detectron2 · dino and dinov2 · opencv
                detection · segmentation · open vocabulary and one shot
   agents       mcp · rag · tool calling · evaluation · claude code · codex
   real time    livekit · streaming stt and tts · diarization · voice agents
   services     fastapi · node and nestjs · rails · next.js · react native
   data         postgresql · postgis · redis
   serving      triton · onnx · tensorrt · docker · kubernetes
   cloud        gcp · aws · railway · supabase
```

### ▍ Public repositories

| Repository | |
|:--|:--|
| [**marrow**](https://github.com/aryawidjaja/marrow) | Persistent, shared memory for AI agents. Markdown native, on premise, auditable. Speaks MCP. |
| [**spinal-cli**](https://github.com/aryawidjaja/spinal-cli) | Installer and command line entry point for the hosted sync relay behind Marrow. |
| [**homebrew-marrow**](https://github.com/aryawidjaja/homebrew-marrow) | Homebrew tap. |
| [**BilayerSmokingDetection**](https://github.com/aryawidjaja/BilayerSmokingDetection) | Two stage smoker detection from CCTV footage, MediaPipe pose landmarks plus a custom VGG16. |
| [**roboflow-fire-leak-detection**](https://github.com/aryawidjaja/roboflow-fire-leak-detection) | Fire and leak detection deployed to a Jetson Orin Nano. |
| [**Payload-Dropping-Mechanism**](https://github.com/aryawidjaja/Payload-Dropping-Mechanism-TDA-Aksantara) | Arduino payload release scheme for a semi automated UAV, built for a university flight team. |
| [**CareCarb-ML**](https://github.com/aryawidjaja/CareCarb-ML) | Transport mode prediction from user coordinates. |

### ▍ Also

B.Eng. Aerospace Engineering from Institut Teknologi Bandung. My thesis, on a 3D printed morphing
wing high lift mechanism for small UAVs, was published in the ISAST 2024 proceedings by Springer.
Machine Learning path at Bangkit Academy by Google.

### ▍ Elsewhere

[mutaqin@aryawijaya.com](mailto:mutaqin@aryawijaya.com) · [linkedin](https://www.linkedin.com/in/mutaqinaryawijaya) · [marrow.works](https://www.marrow.works/)

```
   · · · · · · · · · · · · · · · · · · · · · · · · · · · · · · · ·
```
