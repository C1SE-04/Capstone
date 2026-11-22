<div align="center">

![Logo](../frontend/public/logo.png)

**International School, Duy Tan University**

# Capstone Project 1

**CMU-SE 450 – C1SE.04**

## User Interface Design Document

**Version 1.0**

**Date: November 01, 2026**

# SocraticKid

## A Pedagogically Safe Agentic Tutor with Dynamic Scaffolding

**Created by <C1SE.04>**

**Nguyen Cao Thong**
**Luu Vu Thien**
**Le Huu Thong**
**Nguyen Gia Bao**

**Approved by**

**MSc. Le Duy Linh**

<u>**UI Design Review Panel Representative:**</u>

| Name | Signature | Date |
|------|-----------|------|
|      |           |      |

<u>**Capstone Project 1 – Mentor:**</u>

| Name | Signature | Date |
|------|-----------|------|
| MSc. Le Duy Linh | | |

</div>

---

<div align="center">

**PROJECT INFORMATION**

</div>

| | | | |
|---|---|---|---|
| **Project acronym** | SK | | |
| **Project Title** | SocraticKid: A Pedagogically Safe Agentic Tutor with Dynamic Scaffolding | | |
| **Start Date** | 21 August 2026 | **End Date** | 06 December 2026 |
| **Lead Institution** | International School, Duy Tan University | | |
| **Project Mentor** | MSc. Le Duy Linh | | |
| **Scrum master / Project Leader & contact details** | Luu Vu Thien<br>Email: warface2005tk@gmail.com<br>Tel: 0919324219<br>ID: 29211140533 | | |
| **Partner Organization** | Duy Tan University | | |
| **Project Web URL** | https://socratickid.vercel.app/ | | |

| **Team members** | Name | Email | Tel |
|---|---|---|---|
| 29219053135 | Nguyen Cao Thong | pandatech0610@gmail.com | 0934909569 |
| 29211140533 | Luu Vu Thien | warface2005tk@gmail.com | 0919324219 |
| 29219038101 | Le Huu Thong | bass030196@gmail.com | 0768463655 |
| 29219053725 | Nguyen Gia Bao | ngbaog@gmail.com | 0938086668 |

| | | | |
|---|---|---|---|
| **Document Title** | User Interface Design | | |
| **Reporting Period** | August 2026 – December 2026 | | |
| **Date** | November 01, 2026 | **File name** | UI_Design_Document_SocraticKid_v1.0.md |
| **URL** | https://github.com/C1SE-04/Capstone/blob/develop/docs/UI_Design_Document_SocraticKid_v1.0.md | | |
| **Access** | Internal / University Review | | |

<div align="center">

**Document History**

</div>

| Version | Date | Comments |
|:-------:|:----:|:---------|
| 1.0 | 01/11/2026 | Initial completed release of SocraticKid User Interface Design Document covering all 19 web screens across Student, Parent (Monitor), Guest, and Admin portals. |

---

<div align="center">

**TABLE OF CONTENT**

</div>

1. [Introduction](#1-introduction)
   - 1.1. [Purpose](#11-purpose)
   - 1.2. [Scope](#12-scope)
2. [Interface Design](#2-interface-design)
   - 2.1. [Landing Page (Home Page)](#21-landing-page-home-page)
   - 2.2. [Authentication Modal (Sign In / Sign Up)](#22-authentication-modal-sign-in--sign-up)
   - 2.3. [Guest Trial Chat Screen (Try Page)](#23-guest-trial-chat-screen-try-page)
   - 2.4. [User Onboarding & Role Setup Screen](#24-user-onboarding--role-setup-screen)
   - 2.5. [Student Overview Dashboard](#25-student-overview-dashboard)
   - 2.6. [Socratic AI Chat Workspace](#26-socratic-ai-chat-workspace)
   - 2.7. [Socratic Notebook & Flashcards Screen](#27-socratic-notebook--flashcards-screen)
   - 2.8. [Streak Leaderboard & Gamification Screen](#28-streak-leaderboard--gamification-screen)
   - 2.9. [Student Account Settings & Family Pairing Screen](#29-student-account-settings--family-pairing-screen)
   - 2.10. [Parent Monitor Dashboard](#210-parent-monitor-dashboard)
   - 2.11. [Parent Link Student Modal](#211-parent-link-student-modal)
   - 2.12. [Parent Notification Settings Screen](#212-parent-notification-settings-screen)
   - 2.13. [Admin KPI Overview Dashboard](#213-admin-kpi-overview-dashboard)
   - 2.14. [Admin User Management Screen](#214-admin-user-management-screen)
   - 2.15. [Admin Curriculum & Content Management Screen](#215-admin-curriculum--content-management-screen)
   - 2.16. [Admin System Prompt & Topic Tuning Screen](#216-admin-system-prompt--topic-tuning-screen)
   - 2.17. [Admin Safety AI Moderation Screen](#217-admin-safety-ai-moderation-screen)
   - 2.18. [Admin Agent Trace & Audit Logs Screen](#218-admin-agent-trace--audit-logs-screen)
   - 2.19. [Admin System Settings & Health Screen](#219-admin-system-settings--health-screen)

---

# 1. Introduction

## 1.1. Purpose

This document provides a comprehensive User Interface Design specification for **SocraticKid**, an intelligent, pedagogically safe Agentic AI tutoring web application tailored for Vietnamese grade 4 to 9 students, supervising parents, and system administrators. 

- It serves as the baseline design blueprint for frontend engineers, UI/UX designers, and QA testers to ensure absolute fidelity between user interface requirements and runtime implementation.
- It facilitates alignment across multidisciplinary stakeholders, enabling systematic review of human-computer interaction, pedagogical scaffolding affordances, accessibility, and visual consistency.

## 1.2. Scope

This document details the visual layouts, UI components, interaction targets, and design requirements across all application modules:

- **UI Design Specifications:** Complete specifications of color palette (Warm Canvas `#F7ECE1`, Primary Terracotta `#C1762A`, Deep Ink `#8C4905`, Secondary Surface `#F1CCA6`), typography (Geist Sans font family), component geometries, responsive behaviors, and viewport stabilization (`100dvh`).
- **Functional Descriptions:** Explicit behavioral mapping for all interactive triggers, buttons, navigation links, modals, drawers, input fields, and asynchronous API actions.
- **Usability Standards:** Compliance with WCAG AA accessibility standards, high-contrast text rendering (`#1C1917` on warm surfaces), touch-friendly sizing (minimum 44px tap targets), anti-AI-slop design principles, and mobile-adaptive interfaces.
- **Audience:** Frontend Developers, Backend Engineers, QA/QC Automation Engineers, UI/UX Designers, Academic Mentors, and Project Assessment Panels.

---

# 2. Interface Design

## 2.1. Landing Page (Home Page)

![Landing Page (Home Page)](TODO_screenshot_path)

| **Landing Page (Home Page)** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Brand Logo | Image | Width: 48px, Height: 48px<br>Rounded: Full | Reload current page or navigate to top of landing page |
| 3 | Navigation Link: Features | Button | Text: #C1762A<br>Hover Text: #8C4905 | Smooth scroll to #features section |
| 4 | Navigation Link: About Us | Button | Text: #C1762A<br>Hover Text: #8C4905 | Smooth scroll to #about section |
| 5 | Navigation Link: Contact | Button | Text: #C1762A<br>Hover Text: #8C4905 | Smooth scroll to #contact section |
| 6 | Sign In Button | Button | Background: #F1CCA6<br>Text: #C1762A<br>Hover Background: #F7AD62<br>Hover Text: #FFFFFF | Open Authentication Modal (Sign In / Sign Up) |
| 7 | User Greeting & Avatar | Card | Text: #C1762A<br>Border: #C1762A<br>Avatar Size: 40px | Visible when logged in; displays user profile status |
| 8 | Sign Out Button | Button | Background: #C1762A<br>Text: #FFFFFF<br>Hover Background: #8C4905 | Call /auth/cancel-onboarding and perform NextAuth signOut |
| 9 | Hero Title: SocraticKid | Text | Text: #C1762A<br>Font Weight: 800 italic | [None] |
| 10 | Hero Subtitle | Text | Text: #C1762A<br>Font Size: 20px | [None] |
| 11 | Pedagogical Philosophy Banner | Card | Background: #F1CCA6<br>Text: #8C4905<br>Border: #F1CCA6 | Highlights core Socratic no-spoonfeeding commitment |
| 12 | Call-to-Action Button | Button | Background: Linear Gradient (#C1762A to #8C4905)<br>Text: #FFFFFF | Navigate to /try for guests, /onboarding for pending users, or role-specific dashboard |
| 13 | Features Header Banner | Bar | Background: #C1762A<br>Text: #FFFFFF | [None] |
| 14 | Deep Learning Feature Card | Card | Background: #FFFFFF<br>Title: #8C4905<br>Text: #7A3E04<br>Border: #F1CCA6 | [None] |
| 15 | Safety & Accuracy Feature Card | Card | Background: #FFFFFF<br>Title: #8C4905<br>Text: #7A3E04<br>Border: #F1CCA6 | [None] |
| 16 | Curriculum Alignment Feature Card | Card | Background: #FFFFFF<br>Title: #8C4905<br>Text: #7A3E04<br>Border: #F1CCA6 | [None] |
| 17 | Footer Container | Bar | Background: #C1762A<br>Text: #F7ECE1 | Contains brand info, quick navigation, policies, and hotline |
| 18 | Social Media Links | Icon | Icons: Facebook, TikTok, YouTube | Navigate to external official media channels |

## 2.2. Authentication Modal (Sign In / Sign Up)

![Authentication Modal (Sign In / Sign Up)](TODO_screenshot_path)

| **Authentication Modal (Sign In / Sign Up)** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #000000 (Opacity: 60%) | [None] |
| 2 | Modal Container Card | Card | Background: #F1CCA6<br>Border Radius: 24px<br>Shadow: 0 20px 25px -5px rgba(0,0,0,0.1) | [None] |
| 3 | Close Modal Button | Button | Icon: X<br>Text: #8C4905 | Close the authentication modal |
| 4 | Mascot Owl Emblem | Image | Width: 80px, Height: 80px<br>Background: #F7ECE1<br>Border: #C1762A | [None] |
| 5 | Modal Title | Text | Text: #8C4905<br>Font Weight: Bold italic | Displays "Welcome!" or "Sign up" depending on active tab |
| 6 | Email / Username Input | Text Box | Background: #F7ECE1<br>Text: #1C1917<br>Focus Ring: #F7AD62<br>Error Border: #EF4444 | User inputs registered email or student username |
| 7 | Password Input | Text Box | Background: #F7ECE1<br>Text: #1C1917<br>Type: password<br>Focus Ring: #F7AD62 | User inputs account password |
| 8 | Confirm Password Input | Text Box | Background: #F7ECE1<br>Text: #1C1917<br>Type: password | Visible only in Sign Up mode; validates password matching |
| 9 | Remember Me Checkbox | Checkbox | Accent: #8C4905<br>Text: #8C4905 | Persist session state across browser restarts |
| 10 | Forgot Password Link | Button | Text: #8C4905 | Trigger password recovery flow |
| 11 | Form Error / Success Message | Text | Error Text: #EF4444<br>Success Text: #8C4905 | Displays real-time validation feedback |
| 12 | Submit Button | Button | Background: Linear Gradient (#C1762A to #8C4905)<br>Text: #FFFFFF | Authenticates credentials or submits user registration |
| 13 | Google OAuth Sign-In Button | Button | Background: #FFFFFF<br>Text: #8C4905<br>Border: #F1CCA6 | Trigger NextAuth Google OAuth authentication flow |
| 14 | Toggle Sign In / Sign Up Mode | Button | Text: #C1762A<br>Hover Text: #8C4905 | Switches form between Login mode and Registration mode |
| 15 | Success Notification Toast | Card | Background: #FFFFFF<br>Border: #10B981<br>Text: #1C1917 | Appears upon successful authentication |

## 2.3. Guest Trial Chat Screen (Try Page)

![Guest Trial Chat Screen (Try Page)](TODO_screenshot_path)

| **Guest Trial Chat Screen (Try Page)** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Guest Top Bar | Bar | Background: #FFFFFF<br>Border Bottom: #F1CCA6 | Houses logo, trial quota badge, and login CTA |
| 3 | Logo & Title | Button | Text: #8C4905<br>Image: /logo.png | Navigate to Home Page (/) |
| 4 | Trial Counter Badge | Card | Background: #F1CCA6<br>Text: #8C4905<br>Border: #C1762A | Displays remaining free trial questions (e.g., "7/10 lượt") |
| 5 | Header Login Button | Button | Background: #C1762A<br>Text: #FFFFFF<br>Hover Background: #8C4905 | Opens AuthForm modal |
| 6 | Chat Message Scroll Area | List | Background: #F7ECE1<br>Max Width: 896px | Scrollable stream of guest dialogue bubbles |
| 7 | Assistant Welcome Message | Card | Background: #FFFFFF<br>Border: #F1CCA6<br>Text: #1C1917 | Introduces SocraticKid and explains trial limits |
| 8 | Quick Question Suggestions | Button | Background: #FFFFFF<br>Text: #8C4905<br>Border: #F1CCA6 | Automatically sends selected prompt to trial tutor |
| 9 | Guest Chat Input Box | Text Box | Background: #FFFFFF<br>Text: #1C1917<br>Border: #F1CCA6 | Textarea for typing math questions; auto-expands |
| 10 | Send Message Button | Button | Background: #C1762A<br>Icon: Send<br>Disabled State: Opacity 50% | Submits guest question with X-Guest-ID HTTP header |
| 11 | Trial Expired Modal Container | Card | Background: #F7ECE1<br>Border: #C1762A<br>Shadow: 2xl | Displays when 10 trial questions quota is exhausted |
| 12 | Trial Expired Lottie Owl | Image | Width: 80px, Height: 80px | Renders idle mascot owl animation |
| 13 | Trial Expired Login CTA Button | Button | Background: #C1762A<br>Text: #FFFFFF | Opens AuthForm modal to unlock unlimited learning |

## 2.4. User Onboarding & Role Setup Screen

![User Onboarding & Role Setup Screen](TODO_screenshot_path)

| **User Onboarding & Role Setup Screen** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Top Brand Bar | Bar | Background: Transparent<br>Text: #8C4905 | Displays SocraticKid branding and header |
| 3 | Onboarding Wizard Container | Card | Background: #FFFFFF<br>Border: #F1CCA6<br>Shadow: 0 10px 15px -3px rgba(0,0,0,0.1) | [None] |
| 4 | Step 1 Title: Select Role | Text | Text: #8C4905<br>Font Weight: Bold | Informs user to designate their platform role |
| 5 | Student Role Option Card | Card | Background: #FFFFFF (Active: #F1CCA6)<br>Border: #C1762A<br>Text: #8C4905 | Selects "STUDENT" role |
| 6 | Parent / Monitor Role Option Card | Card | Background: #FFFFFF (Active: #F1CCA6)<br>Border: #C1762A<br>Text: #8C4905 | Selects "MONITOR" role |
| 7 | Grade Level Selector Group | Button Toggle | 6 Pills: Grade 4 to Grade 9<br>Active Background: #C1762A<br>Active Text: #FFFFFF | Selects student math curriculum grade level |
| 8 | Parent Email Input Field | Text Box | Background: #F7ECE1<br>Text: #1C1917<br>Border: #F1CCA6 | Visible when Parent role selected; inputs notification email |
| 9 | Send OTP Verification Button | Button | Background: #C1762A<br>Text: #FFFFFF | Triggers OTP dispatch to designated parent email |
| 10 | OTP Code Input Field | Text Box | Background: #F7ECE1<br>Text: #1C1917 | Inputs 6-digit verification code |
| 11 | Complete Setup Button | Button | Background: Linear Gradient (#C1762A to #8C4905)<br>Text: #FFFFFF | Submits role & grade to /auth/onboarding and enters platform |
| 12 | Cancel & Sign Out Button | Button | Text: #8C4905<br>Hover Text: #C1762A | Calls /auth/cancel-onboarding and clears session |

## 2.5. Student Overview Dashboard

![Student Overview Dashboard](TODO_screenshot_path)

| **Student Overview Dashboard** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Student Navigation Sidebar | Bar | Background: #F1CCA6<br>Border Right: #C1762A/20 | Global dashboard navigation bar |
| 3 | Welcome Heading | Text | Text: #8C4905<br>Font Size: 32px<br>Font Weight: 800 | Displays personalized student greeting with name |
| 4 | Encouragement Subtitle | Text | Text: #C1762A<br>Font Size: 18px | [None] |
| 5 | Daily Streak Flame Summary Card | Card | Background: #FFFFFF<br>Border: #F1CCA6<br>Icon: Flame | Displays current streak days count and flame tier |
| 6 | Recommended Lessons Section Header | Bar | Accent Bar: #F1CCA6<br>Text: #8C4905 | [None] |
| 7 | Math Lesson Cards Grid | List | Background: Transparent<br>Grid Columns: 1 to 3 | Displays curriculum lesson recommendations |
| 8 | Lesson Card Item | Card | Background: #FFFFFF<br>Border: #F1CCA6<br>Title: #8C4905 | Renders lesson thumbnail, title, grade, and duration |
| 9 | Start Lesson Button | Button | Background: #C1762A<br>Text: #FFFFFF<br>Hover Background: #8C4905 | Opens Socratic AI Chat Workspace initialized with lesson topic |
| 10 | Quick Navigation: Socratic Chat | Button | Icon: MessageSquare<br>Text: #8C4905 | Navigate to /dashboard/chat |
| 11 | Quick Navigation: Notebook | Button | Icon: BookMarked<br>Text: #8C4905 | Navigate to /dashboard/notebook |
| 12 | Quick Navigation: Leaderboard | Button | Icon: Trophy<br>Text: #8C4905 | Navigate to /dashboard/leaderboard |

## 2.6. Socratic AI Chat Workspace

![Socratic AI Chat Workspace](TODO_screenshot_path)

| **Socratic AI Chat Workspace** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Left Chat History Sidebar | Bar | Background: #F1CCA6<br>Border Right: #C1762A/20<br>Width: 256px | Contains session history, new chat CTA, and navigation links |
| 3 | New Chat Action Button | Button | Background: #FFFFFF<br>Text: #8C4905<br>Icon: Plus | Clears current dialogue and creates new tutoring session |
| 4 | Chat Sessions History List | List | Grouped by Date (Today, Yesterday, Older)<br>Active Item: #FFFFFF | Switches between prior math conversation sessions |
| 5 | Mastery Progress Bar Component | Bar | Background: #E4DFDF<br>Progress Fill: #10B981<br>Text: #8C4905 | Visualizes student independence score (0-100%) |
| 6 | Streak Flame Live Badge | Card | Background: #FFFFFF<br>Border: #F1CCA6<br>Lottie: streak_flame | Displays animated flame and active consecutive days |
| 7 | Assistant Owl Mascot Animation | Image | Lottie Vector (Animations: idle, thinking, suggesting, correct) | Reflects AI agent emotional state and scaffolding level |
| 8 | Dialogue Message Stream | List | Height: 100dvh - header/input<br>Auto-scroll | Displays student and AI dialogue bubbles |
| 9 | Student Message Bubble | Card | Background: #C1762A<br>Text: #FFFFFF<br>Border Radius: 16px | Displays question submitted by student |
| 10 | Socratic Tutor Message Bubble | Card | Background: #FFFFFF<br>Border: #F1CCA6<br>Text: #1C1917 | Displays Socratic guidance with LaTeX formula rendering |
| 11 | Understanding Buttons ("Đã hiểu" / "Chưa hiểu") | Button Toggle | Understood: #10B981<br>Not Understood: #F59E0B | Submits comprehension feedback; adjusts scaffolding level |
| 12 | Save Bookmark Flashcard Button | Button | Icon: Star / BookMarked<br>Text: #8C4905 | Opens SavePlaylistModal to store problem into Notebook |
| 13 | Chat Input Textarea | Text Box | Background: #FFFFFF<br>Border: #F1CCA6<br>Text: #1C1917 | Auto-expanding input for typing math equations |
| 14 | Attach Math Problem Image Button | Button | Icon: Plus / Camera<br>Text: #8C4905 | Triggers image file picker or mobile camera capture |
| 15 | Image Attachment Thumbnail Preview | Image | Width: 60px, Height: 60px<br>Border: #C1762A | Displays uploaded image preview with remove (X) button |
| 16 | Send Message Trigger Button | Button | Background: #C1762A<br>Icon: Send<br>Text: #FFFFFF | Submits question, image, and formulas to Socratic Agent |
| 17 | Right Exercise Image Drawer Toggle | Button | Icon: PanelRight<br>Text: #8C4905 | Toggles right sidebar displaying original problem images |
| 18 | Idle Study Reminder Modal (10 min) | Card | Background: #F7ECE1<br>Border: #C1762A<br>Title: #8C4905 | Prompts student when inactive for 10 minutes |
| 19 | Badge Unlock Celebration Modal | Card | Background: #FFFFFF<br>Fireworks Lottie<br>Title: #8C4905 | Celebrates unlocking badges (e.g., Tự lập nhí 100đ) |

## 2.7. Socratic Notebook & Flashcards Screen

![Socratic Notebook & Flashcards Screen](TODO_screenshot_path)

| **Socratic Notebook & Flashcards Screen** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Playlist Categories Sidebar | Bar | Background: #F1CCA6<br>Border Right: #C1762A/20 | Lists user-created problem collections and playlists |
| 3 | Create New Playlist Button | Button | Background: #FFFFFF<br>Text: #8C4905<br>Icon: Plus | Opens CreatePlaylistModal to create new folder |
| 4 | Search Notebook Search Bar | Text Box | Background: #FFFFFF<br>Border: #F1CCA6<br>Icon: Search | Real-time filter for bookmarked math questions |
| 5 | Score Filter Tabs | Tab | Options: Tất cả, Điểm tối đa (100đ), Đã hoàn thành<br>Active: #C1762A | Filters flashcards by independence score achievement |
| 6 | Image Attachment Filter Checkbox | Checkbox | Accent: #C1762A<br>Text: #8C4905 | Filters for math problems that include image attachments |
| 7 | Flashcards Grid / List | List | Max Width: 1200px<br>10 cards per page | Renders problem cards with formulas and summaries |
| 8 | Flashcard Item Card | Card | Background: #FFFFFF<br>Border: #F1CCA6<br>Text: #1C1917 | Displays problem question, core takeaway tip, and score |
| 9 | Review Conversation Button | Button | Icon: ArrowRight<br>Text: #C1762A | Slides open BookmarkChatDrawer to review dialogue steps |
| 10 | Delete Bookmark Button | Button | Icon: Trash2<br>Text: #EF4444 | Removes problem bookmark from active playlist |
| 11 | Bookmark Chat Drawer | Card | Background: #FFFFFF<br>Width: 420px<br>Border Left: #F1CCA6 | Slide-over drawer rendering complete Socratic chat steps |
| 12 | Notebook Pagination Bar | Bar | Active Page: #C1762A<br>Text: #8C4905 | Navigates across pages (10 problems per page) |

## 2.8. Streak Leaderboard & Gamification Screen

![Streak Leaderboard & Gamification Screen](TODO_screenshot_path)

| **Streak Leaderboard & Gamification Screen** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Leaderboard Header Banner | Bar | Text: #8C4905<br>Icon: Trophy | Displays leaderboard title and motivational badge |
| 3 | Grade Level Filter Bar | Tab | Options: Toàn Server, Khối 4, 5, 6, 7, 8, 9<br>Active: #C1762A | Switches ranking scope by school grade |
| 4 | Manual Refresh Button | Button | Background: #FFFFFF<br>Icon: RefreshCw<br>Text: #8C4905 | Reloads latest leaderboard standings from API |
| 5 | Top 3 Podium Component | Card | Gold, Silver, Bronze Stands<br>Avatars & Flame Badges | Celebrates top 3 leading students on platform |
| 6 | Gold First Place Podium Step | Card | Stand Background: #F59E0B<br>Text: #FFFFFF | Displays rank 1 student with highest streak |
| 7 | Silver Second Place Podium Step | Card | Stand Background: #94A3B8<br>Text: #FFFFFF | Displays rank 2 student |
| 8 | Bronze Third Place Podium Step | Card | Stand Background: #D97706<br>Text: #FFFFFF | Displays rank 3 student |
| 9 | Your Current Rank Card | Card | Background: #FFFFFF<br>Border: #C1762A<br>Shadow: 0 4px 6px -1px rgba(0,0,0,0.1) | Displays current user's standing, streak, and tier |
| 10 | Leaderboard Standings Table | List | Table Header: #F1CCA6<br>Row Hover: #F7ECE1 | Renders top 50 ranked students anonymously |
| 11 | Table Row Item | Card | Text: #1C1917<br>Flame Icon: STREAK_TIER | Shows rank number, nickname, streak days, and grade |
| 12 | 7-Tier Flame Evolution Guide Modal | Card | Background: #FFFFFF<br>Border: #F1CCA6 | Explains streak flame tiers from 1-day ember to 100-day flame |

## 2.9. Student Account Settings & Family Pairing Screen

![Student Account Settings & Family Pairing Screen](TODO_screenshot_path)

| **Student Account Settings & Family Pairing Screen** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Settings Header Title | Text | Text: #8C4905<br>Font Size: 28px<br>Font Weight: Bold | [None] |
| 3 | Account Profile Summary Card | Card | Background: #FFFFFF<br>Border: #F1CCA6 | Displays student display name, registered email, and role |
| 4 | Change Grade Level Section | Card | Background: #FFFFFF<br>Border: #F1CCA6 | Allows updating current math grade level |
| 5 | Grade Selection Pills (4 to 9) | Button Toggle | Active: #C1762A<br>Inactive: #F1CCA6<br>Text: #8C4905 | Selects target school grade |
| 6 | Save Grade Level Button | Button | Background: #C1762A<br>Text: #FFFFFF | Submits grade change and triggers BroadcastChannel sync |
| 7 | Grade Change Confirmation Dialog | Card | Background: #FFFFFF<br>Border: #EF4444<br>Text: #1C1917 | Warns that curriculum difficulty and tutor will adjust |
| 8 | Family Pairing Code Generator Card | Card | Background: #FFFFFF<br>Border: #F1CCA6 | Manages linking code for parents to monitor progress |
| 9 | 6-Digit Family Pairing Code Display | Text | Text: #8C4905<br>Letter Spacing: 6px<br>Font Size: 32px | Displays generated 6-character linking code |
| 10 | Copy Pairing Code Button | Button | Background: #F1CCA6<br>Text: #8C4905 | Copies pairing code to clipboard with visual checkmark feedback |
| 11 | Code Countdown Timer | Text | Text: #C1762A<br>Format: MM:SS | Displays remaining validity time (15 minutes expiry) |
| 12 | Generate New Code Button | Button | Background: #C1762A<br>Text: #FFFFFF | Requests fresh pairing code from backend |

## 2.10. Parent Monitor Dashboard

![Parent Monitor Dashboard](TODO_screenshot_path)

| **Parent Monitor Dashboard** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Monitor Navigation Sidebar | Bar | Background: #F1CCA6<br>Border Right: #C1762A/20 | Contains child switcher, notification settings, and sign-out |
| 3 | Linked Children Switcher List | List | Active Child Card: #FFFFFF<br>Text: #8C4905 | Switches data view between linked sons/daughters |
| 4 | Add Child Button | Button | Icon: UserPlus<br>Text: #8C4905<br>Background: #FFFFFF | Opens LinkStudentModal to link child using 6-digit code |
| 5 | Child Overview Header | Bar | Text: #8C4905<br>Grade Badge: #C1762A | Displays active child's nickname and school grade |
| 6 | Weekly Navigation Control | Button Toggle | Prev Week (<), Next Week (>), Current Week<br>Text: #8C4905 | Navigates backward/forward through weekly analytics |
| 7 | Summary Metrics Cards Row | List | 3 Cards (Total Minutes, Problems Solved, Avg Independence) | Key performance indicators for active child |
| 8 | Weekly Study Hours Line Chart | Card | Background: #FFFFFF<br>Chart Line: #C1762A<br>Recharts Component | Plots daily study time in minutes/hours across Monday-Sunday |
| 9 | Independence Score Trend Chart | Card | Background: #FFFFFF<br>Chart Line: #10B981<br>Range: 0-100 | Tracks student cognitive self-reliance progression |
| 10 | Pedagogical AI Insights Card | Card | Background: #FFFFFF<br>Border: #F1CCA6<br>Text: #8C4905 | AI pedagogical summary evaluating strengths & misconceptions |
| 11 | Child Problem Solving History List | List | Background: #FFFFFF<br>Border: #F1CCA6 | Itemized log of math questions solved by child with images |
| 12 | Unlink Student Button | Button | Icon: Trash2<br>Text: #EF4444 | Removes linked student from parent monitor list |

## 2.11. Parent Link Student Modal

![Parent Link Student Modal](TODO_screenshot_path)

| **Parent Link Student Modal** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #000000 (Opacity: 50%) | [None] |
| 2 | Modal Container Card | Card | Background: #F7ECE1<br>Border: #F1CCA6<br>Border Radius: 24px | [None] |
| 3 | Close Modal Button | Button | Icon: X<br>Text: #8C4905 | Closes linking modal dialog |
| 4 | Modal Title | Text | Text: #8C4905<br>Font Size: 24px<br>Font Weight: Bold | Displays "Liên kết tài khoản của con" |
| 5 | Instructional Description | Text | Text: #C1762A<br>Font Size: 14px | Explains how student generates code in Settings |
| 6 | 6-Digit Split Code Input Boxes | Text Box | 6 Separate Input Cells<br>Background: #FFFFFF<br>Focus Ring: #C1762A | User inputs student's 6-digit alphanumeric pairing code |
| 7 | Validation Error Message | Text | Text: #EF4444<br>Font Weight: Bold | Appears when code is expired, invalid, or already linked |
| 8 | Success Confirmation Message | Text | Text: #10B981<br>Icon: CheckCircle2 | Confirms successful pairing with student's name |
| 9 | Submit Pairing Code Button | Button | Background: #C1762A<br>Text: #FFFFFF<br>Hover Background: #8C4905 | Submits code to POST /family/link-student |

## 2.12. Parent Notification Settings Screen

![Parent Notification Settings Screen](TODO_screenshot_path)

| **Parent Notification Settings Screen** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Back to Monitor Dashboard Button | Button | Icon: ArrowLeft<br>Text: #8C4905 | Navigates back to /dashboard/monitor |
| 3 | Settings Header Title | Text | Text: #8C4905<br>Font Size: 28px<br>Font Weight: Bold | [None] |
| 4 | Account Information Card | Card | Background: #FFFFFF<br>Border: #F1CCA6 | Displays parent account email and OAuth provider |
| 5 | Alert Notification Email Card | Card | Background: #FFFFFF<br>Border: #F1CCA6 | Configure email address for safety and weekly digest reports |
| 6 | Notification Email Input Field | Text Box | Background: #F7ECE1<br>Text: #1C1917<br>Border: #F1CCA6 | Edits recipient email (disabled if logged in via Google) |
| 7 | Google OAuth Lock Notice | Text | Text: #C1762A<br>Icon: Lock | Informs user that Google email is permanently bound |
| 8 | Save Notification Email Button | Button | Background: #C1762A<br>Text: #FFFFFF | Sends PATCH /users/me/notification-email |
| 9 | Success Toast Indicator | Card | Background: #ECFDF5<br>Border: #10B981<br>Text: #10B981 | Displays confirmation when email update succeeds |

## 2.13. Admin KPI Overview Dashboard

![Admin KPI Overview Dashboard](TODO_screenshot_path)

| **Admin KPI Overview Dashboard** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Admin Global Navigation Sidebar | Bar | Background: #F1CCA6<br>Border Right: #C1762A/20 | Admin module navigation (Users, Content, Safety, Logs, Settings) |
| 3 | KPI Header Title | Text | Text: #8C4905<br>Font Size: 28px<br>Font Weight: Bold | Displays "KPI Dashboard & Phân Tích Hệ Thống" |
| 4 | Metric Time Range Selector | Button Toggle | Options: 7 ngày, 14 ngày, 30 ngày<br>Active: #C1762A | Adjusts historical window for KPI calculations |
| 5 | Total Users Stat Card | Card | Background: #FFFFFF<br>Border: #F1CCA6<br>Icon: Users | Shows total registered students, parents, and admins |
| 6 | Active Tutoring Sessions Stat Card | Card | Background: #FFFFFF<br>Border: #F1CCA6<br>Icon: MessageSquare | Total dialogues conducted by Socratic tutoring agents |
| 7 | Safety Flag Alerts Stat Card | Card | Background: #FFFFFF<br>Border: #F1CCA6<br>Icon: ShieldAlert | Total content moderation flags intercepted by Reviewer |
| 8 | Total API Cost & Tokens Card | Card | Background: #FFFFFF<br>Border: #F1CCA6<br>Icon: Cpu | Displays LLM prompt/completion tokens and estimated USD cost |
| 9 | Token Consumption & Latency Chart | Card | Background: #FFFFFF<br>Border: #F1CCA6<br>ComposedChart (Bar + Line) | Dual-axis graph plotting daily tokens vs model response latency |
| 10 | Quick Action: Inspect Safety Violations | Button | Background: #FFFFFF<br>Text: #8C4905<br>Icon: ArrowRight | Navigates directly to /admin/safety |
| 11 | Quick Action: Manage Curriculum | Button | Background: #FFFFFF<br>Text: #8C4905<br>Icon: ArrowRight | Navigates directly to /admin/content |

## 2.14. Admin User Management Screen

![Admin User Management Screen](TODO_screenshot_path)

| **Admin User Management Screen** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | User Management Header | Bar | Text: #8C4905<br>Count Badge: #C1762A | Title bar with user count and breadcrumbs |
| 3 | User Search Input Box | Text Box | Background: #FFFFFF<br>Border: #F1CCA6<br>Icon: Search | Searches users by name, student ID, or email |
| 4 | Role Filter Dropdown | Dropdown | Options: Tất cả vai trò, STUDENT, MONITOR, ADMIN | Filters user list by system permission role |
| 5 | Account Status Filter Tabs | Tab | Options: Tất cả, ACTIVE, BANNED, PENDING | Filters users by account activation state |
| 6 | Export Users CSV Button | Button | Background: #FFFFFF<br>Text: #8C4905<br>Icon: Download | Exports filtered user table to CSV spreadsheet |
| 7 | User Roster Data Table | List | Table Header: #F1CCA6<br>Zebra Striping | Displays user account rows with metadata |
| 8 | User Name & Email Column | Text | Name: #8C4905 (Bold)<br>Email: #7A3E04 | [None] |
| 9 | Role Badge Indicator | Card | STUDENT: #3B82F6<br>MONITOR: #10B981<br>ADMIN: #8C4905 | Visual pill indicating account role |
| 10 | Grade & Metrics Column | Text | Text: #1C1917 | Displays grade level, streak days, and solved problems |
| 11 | Account Status Badge | Card | ACTIVE: Green<br>BANNED: Red | Indicates whether user is allowed platform access |
| 12 | Ban / Unban User Action Button | Button | Ban: #EF4444<br>Unban: #10B981 | Toggles user access status with confirmation prompt |
| 13 | View Linked Family Details Button | Button | Icon: Eye<br>Text: #8C4905 | Opens modal showing connected parent/children |
| 14 | Table Pagination Controls | Bar | Previous, Next, Page Numbers<br>Active: #C1762A | Navigates pages of user directory |

## 2.15. Admin Curriculum & Content Management Screen

![Admin Curriculum & Content Management Screen](TODO_screenshot_path)

| **Admin Curriculum & Content Management Screen** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Curriculum Management Header | Bar | Text: #8C4905<br>Icon: BookOpen | Displays screen title and breadcrumb navigation |
| 3 | Sync Vietjack Textbook Button | Button | Background: #C1762A<br>Text: #FFFFFF<br>Icon: RefreshCw | Opens SyncVietjackModal to fetch latest textbooks |
| 4 | Grade Filter Selector | Dropdown | Options: Tất cả khối lớp, Lớp 4, 5, 6, 7, 8, 9 | Filters curriculum topics by grade level |
| 5 | Semester Filter Selector | Dropdown | Options: Tất cả học kỳ, Học kỳ 1, Học kỳ 2 | Filters topics by school semester |
| 6 | Search Curriculum Input | Text Box | Background: #FFFFFF<br>Border: #F1CCA6<br>Icon: Search | Searches topics by math lesson name or keyword |
| 7 | Curriculum Topics Table | List | Table Header: #F1CCA6<br>Border: #F1CCA6 | Lists math units, chapter names, and lesson counts |
| 8 | Topic Order & Title Cell | Text | Order Badge: #F1CCA6<br>Topic Name: #8C4905 | Displays sequential order and topic name |
| 9 | Grade & Semester Badge | Card | Background: #F7ECE1<br>Text: #C1762A | Indicates target grade level and semester |
| 10 | Active Status Toggle Switch | Switch | Active: #10B981<br>Inactive: #94A3B8 | Enables or disables topic for student AI lessons |
| 11 | Prompt Tuning Quick Link | Button | Icon: Sparkles<br>Text: #C1762A | Navigates to /admin/content/prompt-topics |
| 12 | Sync Vietjack Modal Dialog | Card | Background: #FFFFFF<br>Border Radius: 20px | Allows selecting specific grade to trigger web scraper |

## 2.16. Admin System Prompt & Topic Tuning Screen

![Admin System Prompt & Topic Tuning Screen](TODO_screenshot_path)

| **Admin System Prompt & Topic Tuning Screen** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Back to Content Management Link | Button | Icon: ArrowLeft<br>Text: #8C4905 | Navigates back to /admin/content |
| 3 | Header Title | Text | Text: #8C4905<br>Font Size: 28px<br>Font Weight: Bold | Displays "Cấu Hình System Prompt Chuyên Đề" |
| 4 | Grade Filter Tabs (4 to 9) | Tab | Active: #C1762A<br>Inactive: #F1CCA6<br>Text: #8C4905 | Filters agent prompts by target math grade |
| 5 | Search Topics Input Field | Text Box | Background: #FFFFFF<br>Border: #F1CCA6 | Filters topic list in real-time |
| 6 | Grade Summary Statistics Card | Card | Background: #FFFFFF<br>Border: #F1CCA6 | Shows active topic count vs inactive topics |
| 7 | Preview System Prompt Button | Button | Background: #C1762A<br>Text: #FFFFFF<br>Icon: Code2 | Opens full-screen modal showing compiled prompt string |
| 8 | Topic List Table | List | Table Header: #F1CCA6<br>Border: #F1CCA6 | Shows lesson topics injected into agent context |
| 9 | Prompt Preview Modal Container | Card | Background: #1C1917<br>Text: #F7ECE1<br>Font: Geist Mono | Renders formatted markdown of Socratic tutor prompt |
| 10 | Copy Prompt to Clipboard Button | Button | Background: #C1762A<br>Text: #FFFFFF<br>Icon: Copy | Copies compiled agent prompt for testing in Gemini Studio |

## 2.17. Admin Safety AI Moderation Screen

![Admin Safety AI Moderation Screen](TODO_screenshot_path)

| **Admin Safety AI Moderation Screen** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Safety Moderation Header | Bar | Text: #8C4905<br>Icon: ShieldAlert | Title bar with alert indicators and stats |
| 3 | Safety Incident Metrics Row | List | 4 Cards (Total Violations, High Severity, Blocked, Warned) | Summary cards of Reviewer Agent interceptions |
| 4 | Violations by Category Bar Chart | Card | Background: #FFFFFF<br>Chart Fill: #EF4444<br>Recharts Bar | Plots incidents across Toxic, Cheating, Off-topic, Privacy |
| 5 | Severity Breakdown Pie Chart | Card | Background: #FFFFFF<br>Pills: Low, Medium, High<br>Recharts Pie | Visualizes distribution of threat levels |
| 6 | Search Safety Logs Input | Text Box | Background: #FFFFFF<br>Border: #F1CCA6<br>Icon: Search | Searches logs by student email, query snippet, or ID |
| 7 | Violation Type Filter Dropdown | Dropdown | Options: Tất cả loại, TOXIC_LANGUAGE, DIRECT_ANSWER_REQUEST, OFF_TOPIC | Filters incident table by violation classification |
| 8 | Severity Filter Dropdown | Dropdown | Options: Tất cả mức độ, LOW, MEDIUM, HIGH, CRITICAL | Filters incident table by risk severity level |
| 9 | Safety Interceptions Log Table | List | Table Header: #F1CCA6<br>Border: #F1CCA6 | Detailed log of intercepted student messages |
| 10 | Severity Badge Indicator | Card | HIGH: #EF4444<br>MEDIUM: #F59E0B<br>LOW: #10B981 | Color-coded risk tag |
| 11 | Message Snippet Column | Text | Text: #1C1917<br>Max Width: 320px | Displays sanitized excerpt of student's flagged query |
| 12 | Agent Action Taken Badge | Card | BLOCKED: Red<br>WARNED: Orange<br>REDIRECTED: Blue | Describes action executed by Reviewer Agent |
| 13 | Inspect Incident Detail Modal Button | Button | Icon: Eye<br>Text: #8C4905 | Opens modal showing prompt, raw output, and user ID |
| 14 | Send Parent Notification Alert Button | Button | Icon: Mail<br>Text: #C1762A | Dispatches manual security email notice to student's parent |

## 2.18. Admin Agent Trace & Audit Logs Screen

![Admin Agent Trace & Audit Logs Screen](TODO_screenshot_path)

| **Admin Agent Trace & Audit Logs Screen** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | Audit Logs Header Title | Text | Text: #8C4905<br>Font Size: 28px<br>Font Weight: Bold | Displays "Tra Cứu Logs & Truy Vết Agentic AI" |
| 3 | Agent Filter Tabs | Tab | Options: Tất cả Agents, Knowledge Tracing, Misconception, Scaffolding, Safety | Filters audit records by executing AI agent |
| 4 | Search Query & Session Input | Text Box | Background: #FFFFFF<br>Border: #F1CCA6<br>Icon: Search | Filters logs by session ID or student query text |
| 5 | Execution Latency & Timestamp Column | Text | Timestamp: #7A3E04<br>Latency: #10B981 (<1500ms) | Displays exact UTC time and response duration |
| 6 | Agent Trace Data Table | List | Table Header: #F1CCA6<br>Monospace Text | Displays structured pipeline execution events |
| 7 | Scaffolding Level Badge | Card | Level 1: Hint, Level 2: Sub-question, Level 3: Concept | Shows pedagogical scaffolding degree applied |
| 8 | Misconception Detected Tag | Card | Background: #FEE2E2<br>Text: #EF4444 | Displays math error concept identified by Misconception Agent |
| 9 | Raw JSON Payload Inspector Button | Button | Icon: Code2<br>Text: #8C4905 | Opens modal showing raw agent input/output JSON payload |
| 10 | Export Audit Logs Button | Button | Background: #FFFFFF<br>Text: #8C4905<br>Icon: Download | Exports audit log trail for compliance reviews |

## 2.19. Admin System Settings & Health Screen

![Admin System Settings & Health Screen](TODO_screenshot_path)

| **Admin System Settings & Health Screen** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: #F7ECE1 | [None] |
| 2 | System Settings Header | Bar | Text: #8C4905<br>System Version: "v1.7.0" | Displays title and build version |
| 3 | Subsystem Health Monitoring Row | List | 4 Cards (PostgreSQL DB, Redis Cache, Gemini API, Cloudinary) | Live status badges (Operational, Latency in ms) |
| 4 | Primary LLM Model Selector | Dropdown | Options: gemini-1.5-flash, gemini-1.5-pro<br>Background: #FFFFFF | Designates default reasoning model for Socratic tutor |
| 5 | Backup LLM Model Selector | Dropdown | Options: gemini-1.5-pro, gemini-1.0-pro<br>Background: #FFFFFF | Designates fallback model when primary model limits trip |
| 6 | Model Temperature Slider | Bar | Range: 0.0 to 1.0<br>Current: 0.35<br>Accent: #C1762A | Adjusts LLM generation randomness and strictness |
| 7 | Max Output Tokens Input | Text Box | Type: number<br>Default: 512<br>Background: #FFFFFF | Caps maximum tokens per agent conversational response |
| 8 | Reviewer Safety Threshold Selector | Dropdown | Options: BLOCK_LOW_AND_ABOVE, BLOCK_MEDIUM_AND_ABOVE | Sets sensitivity threshold for toxic content filtering |
| 9 | Guest Rate Limit Daily Quota Field | Text Box | Type: number<br>Default: 10<br>Background: #FFFFFF | Defines maximum free trial questions allowed per IP/Guest |
| 10 | Multimodal Math Vision Support Switch | Switch | Active: #10B981<br>Inactive: #94A3B8 | Toggles image recognition capabilities for math problems |
| 11 | Automated Parent Alerts Switch | Switch | Active: #10B981<br>Inactive: #94A3B8 | Enables automatic email dispatch to parents on safety flags |
| 12 | Save Settings Button | Button | Background: #C1762A<br>Text: #FFFFFF<br>Icon: Save | Commits updated configuration to backend configuration store |
| 13 | Reset to Factory Defaults Button | Button | Background: #FFFFFF<br>Text: #EF4444<br>Icon: RotateCcw | Restores original benchmark parameters |

