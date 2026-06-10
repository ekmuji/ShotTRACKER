# ShotTRACKER

# Basketball Shot Tracker (iPhone)

## Project Overview

An iPhone application that uses the device camera and computer vision to automatically track basketball shots made and missed during shooting workouts.

The app will calculate shooting percentage in real time and store workout history for later analysis.



# Step 1: Define the Project

## What is the Project?

A native iOS application that:

* Uses the iPhone camera to observe a basketball hoop and player.
* Detects shot attempts.
* Determines whether each shot is made or missed.
* Calculates shooting percentage.
* Stores workout sessions and statistics.

The goal is to provide players with automatic shooting analytics without requiring manual scorekeeping.


## MVP (Minimum Viable Product)

### Core Features

* Live camera feed
* Basketball detection
* Hoop detection
* Shot attempt detection
* Made shot detection
* Missed shot detection
* Live shooting percentage
* Workout session tracking
* Local data storage
* iOS 17+ support

### MVP Success Criteria

The MVP is successful when:

* User places iPhone on a tripod.
* App automatically counts makes and misses.
* Shooting percentage updates in real time.
* User can save and review workout sessions.



## Nice-to-Have Features

### Analytics

* Shot charts
* Hot/cold zones
* Daily, weekly and monthly trends
* Personal bests

### AI Features

* Arc analysis
* Release speed estimation
* Shot consistency scoring
* AI coaching recommendations

### Social Features

* Leaderboards
* Friend challenges
* Team accounts

### Platform Features

* iCloud sync
* Apple Watch support
* Dark mode customization
* Export workout data



## Definition of Complete

Version 1.0 is complete when:

* App successfully detects makes and misses.
* Accuracy exceeds 85% under recommended camera placement.
* Workout data is saved and retrievable.
* App functions on iOS 17 and newer devices.
* Beta testing has been completed through TestFlight.

# Step 2: Create the Workflow

## Development Workflow

### Phase 1 – Research & Planning

* Define requirements
* Evaluate existing basketball datasets
* Evaluate YOLO models
* Design system architecture
* Design user interface

### Phase 2 – Computer Vision Prototype

* Build Python proof of concept
* Detect basketball
* Detect hoop
* Test shot tracking logic
* Validate accuracy

### Phase 3 – iOS Development

* Create SwiftUI application
* Integrate camera feed
* Integrate Core ML model
* Implement shot tracking engine
* Build statistics screens

### Phase 4 – Testing & Optimization

* Court testing
* Performance optimization
* Battery optimization
* Accuracy improvements
* Bug fixes

### Phase 5 – Release

* TestFlight beta
* Collect feedback
* Final bug fixes
* App Store submission



# Step 3: Break Project into Components

## Component 1: Project Setup

* Repository
* Documentation
* Development environment
* Architecture planning

## Component 2: Computer Vision

* Dataset collection
* Model selection
* Model conversion
* Ball detection
* Hoop detection

## Component 3: Shot Tracking Engine

* Ball tracking
* Hoop tracking
* Trajectory analysis
* Shot attempt detection
* Make/miss detection

## Component 4: Camera System

* Camera permissions
* AVFoundation integration
* Live video feed
* Frame processing

## Component 5: User Interface

* Home screen
* Workout screen
* Statistics screen
* Session history screen

## Component 6: Data Storage

* Session storage
* Statistics storage
* Workout history

## Component 7: Testing

* Unit tests
* Device testing
* Court testing
* Beta testing

## Component 8: Deployment

* TestFlight
* App Store assets
* App Store submission



# Step 3a: Break Components into Checklists

## Component 1: Project Setup

### Checklist

* [ ] Create Git repository
* [ ] Configure project structure
* [ ] Create README
* [ ] Define coding standards
* [ ] Create development roadmap


## Component 2: Computer Vision

### Dataset

* [ ] Research basketball datasets
* [ ] Research hoop datasets
* [ ] Download training data
* [ ] Label missing images

### Model Selection

* [ ] Evaluate YOLOv8n
* [ ] Evaluate YOLOv11
* [ ] Benchmark performance

### Model Conversion

* [ ] Export to Core ML
* [ ] Verify model loading
* [ ] Verify inference speed

### Detection

* [ ] Detect basketball
* [ ] Detect hoop
* [ ] Draw bounding boxes
* [ ] Verify accuracy



## Component 3: Shot Tracking Engine

### Ball Tracking

* [ ] Track ball across frames
* [ ] Store coordinates
* [ ] Calculate velocity

### Shot Detection

* [ ] Detect upward motion
* [ ] Detect shot attempts
* [ ] Detect ball entering hoop area

### Make/Miss Logic

* [ ] Register made shot
* [ ] Register missed shot
* [ ] Prevent duplicate counts

### Statistics

* [ ] Count shots taken
* [ ] Count shots made
* [ ] Calculate percentage



## Component 4: Camera System

### Camera Integration

* [ ] Request permissions
* [ ] Configure AVCaptureSession
* [ ] Display live feed

### Frame Processing

* [ ] Capture video frames
* [ ] Pass frames to Vision
* [ ] Handle processing queue



## Component 5: User Interface

### Home Screen

* [ ] Start workout
* [ ] View history
* [ ] Settings

### Workout Screen

* [ ] Camera view
* [ ] Makes counter
* [ ] Misses counter
* [ ] Percentage display

### Statistics Screen

* [ ] Session summary
* [ ] Historical performance
* [ ] Charts



## Component 6: Data Storage

### Local Storage

* [ ] Save workout
* [ ] Load workout history
* [ ] Delete workout

### Future Cloud Sync

* [ ] Supabase integration
* [ ] User authentication
* [ ] Data synchronization



## Component 7: Testing

### Functional Testing

* [ ] Ball detection test
* [ ] Hoop detection test
* [ ] Make detection test
* [ ] Miss detection test

### Device Testing

* [ ] iPhone running iOS 17
* [ ] Latest iPhone version
* [ ] Performance testing

### Real Court Testing

* [ ] Indoor court
* [ ] Outdoor court
* [ ] Different lighting conditions



## Component 8: Deployment

### TestFlight

* [ ] Create beta build
* [ ] Invite testers
* [ ] Collect feedback

### App Store

* [ ] App description
* [ ] Screenshots
* [ ] Privacy policy
* [ ] Submit for review


# Recommended Technology Stack

## iOS

* Swift
* SwiftUI
* AVFoundation
* Vision Framework
* Core ML

## AI / Computer Vision

* YOLOv8n
* Roboflow Datasets
* Core ML Export

## Backend (Future)

* Supabase
* PostgreSQL

## Development Tools

* Xcode
* GitHub
* TestFlight



# Initial Release Goal

Target completion:

12–16 weeks

Target release:

Version 1.0 with automatic make/miss tracking and real-time shooting percentage.
