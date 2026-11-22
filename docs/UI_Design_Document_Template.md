<!--
TEMPLATE: User Interface Design Document
Quy ước: mọi chỗ cần điền đều ở dạng {{TEN_BIEN}}.
Khối "SCREEN BLOCK" ở mục 2 được lặp lại cho MỖI màn hình (đánh số 2.1, 2.2, ...).
-->

<div align="center">

![Logo]({{LOGO_PATH}})

**{{SCHOOL_NAME}}**

# {{COURSE_NAME}}

**{{COURSE_CODE}} – {{TEAM_CODE}}**

## User Interface Design Document

**Version {{VERSION}}**

**Date: {{DOCUMENT_DATE}}**

# {{PROJECT_NAME}}

## {{PROJECT_SUBTITLE}}

**Created by <{{TEAM_CODE}}>**

**{{MEMBER_1_NAME}}**
**{{MEMBER_2_NAME}}**
**{{MEMBER_3_NAME}}**
**{{MEMBER_N_NAME}}**

**Approved by**

**{{MENTOR_NAME}}**

<u>**UI Design Review Panel Representative:**</u>

| Name | Signature | Date |
|------|-----------|------|
|      |           |      |

<u>**{{COURSE_NAME}} – Mentor:**</u>

| Name | Signature | Date |
|------|-----------|------|
|      |           |      |

</div>

---

<div align="center">

**PROJECT INFORMATION**

</div>

| | | | |
|---|---|---|---|
| **Project acronym** | {{PROJECT_ACRONYM}} | | |
| **Project Title** | {{PROJECT_TITLE}} | | |
| **Start Date** | {{START_DATE}} | **End Date** | {{END_DATE}} |
| **Lead Institution** | {{LEAD_INSTITUTION}} | | |
| **Project Mentor** | {{MENTOR_NAME}} | | |
| **Scrum master / Project Leader & contact details** | {{LEADER_NAME}}<br>Email: {{LEADER_EMAIL}}<br>Tel: {{LEADER_PHONE}}<br>ID: {{LEADER_STUDENT_ID}} | | |
| **Partner Organization** | {{PARTNER_ORGANIZATION}} | | |
| **Project Web URL** | {{PROJECT_URL}} | | |

| **Team members** | Name | Email | Tel |
|---|---|---|---|
| {{MEMBER_1_ID}} | {{MEMBER_1_NAME}} | {{MEMBER_1_EMAIL}} | {{MEMBER_1_PHONE}} |
| {{MEMBER_2_ID}} | {{MEMBER_2_NAME}} | {{MEMBER_2_EMAIL}} | {{MEMBER_2_PHONE}} |
| {{MEMBER_N_ID}} | {{MEMBER_N_NAME}} | {{MEMBER_N_EMAIL}} | {{MEMBER_N_PHONE}} |

| | | | |
|---|---|---|---|
| **Document Title** | User Interface Design | | |
| **Reporting Period** | {{REPORTING_PERIOD}} | | |
| **Date** | {{DOCUMENT_DATE}} | **File name** | {{FILE_NAME}} |
| **URL** | {{DOCUMENT_URL}} | | |
| **Access** | {{ACCESS}} | | |

<div align="center">

**Document History**

</div>

| Version | Date | Comments |
|:-------:|:----:|:---------|
| {{VERSION_1}} | {{VERSION_1_DATE}} | {{VERSION_1_COMMENT}} |
| {{VERSION_2}} | {{VERSION_2_DATE}} | {{VERSION_2_COMMENT}} |

---

<div align="center">

**TABLE OF CONTENT**

</div>

<!-- Liệt kê toàn bộ heading cấp 1, 1.x, 2, 2.x theo đúng thứ tự trong tài liệu -->

1. [Introduction](#1-introduction)
   - 1.1. [Purpose](#11-purpose)
   - 1.2. [Scope](#12-scope)
2. [Interface Design](#2-interface-design)
   - 2.1. [{{SCREEN_1_NAME}}](#{{SCREEN_1_ANCHOR}})
   - 2.2. [{{SCREEN_2_NAME}}](#{{SCREEN_2_ANCHOR}})
   - 2.N. [{{SCREEN_N_NAME}}](#{{SCREEN_N_ANCHOR}})

---

# 1. Introduction

## 1.1. Purpose

{{PURPOSE_INTRO_SENTENCE}}

- {{PURPOSE_BULLET_1}}
- {{PURPOSE_BULLET_2}}

## 1.2. Scope

{{SCOPE_INTRO_SENTENCE}}

- **UI Design Specifications:** {{SCOPE_UI_SPEC}}
- **Functional Descriptions:** {{SCOPE_FUNCTIONAL}}
- **Usability Standards:** {{SCOPE_USABILITY}}
- **Audience:** {{SCOPE_AUDIENCE}}

---

# 2. Interface Design

<!-- ===================== SCREEN BLOCK (lặp lại cho mỗi màn hình) ===================== -->

## 2.1. {{SCREEN_1_NAME}}

<!-- Ảnh giao diện: 1 hoặc nhiều ảnh đặt cạnh nhau -->
![{{SCREEN_1_NAME}} – ảnh 1]({{SCREEN_1_IMAGE_1}}) ![{{SCREEN_1_NAME}} – ảnh 2]({{SCREEN_1_IMAGE_2}})

| **{{SCREEN_1_NAME}}** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: {{COLOR_HEX}} | [None] |
| 2 | {{FIELD_NAME}} | {{TYPE}} | {{REQUIRE}} | {{TARGET}} |
| 3 | {{FIELD_NAME}} | {{TYPE}} | {{REQUIRE}} | {{TARGET}} |
| N | {{FIELD_NAME}} | {{TYPE}} | {{REQUIRE}} | {{TARGET}} |

<!-- ===================== END SCREEN BLOCK ===================== -->

## 2.2. {{SCREEN_2_NAME}}

![{{SCREEN_2_NAME}}]({{SCREEN_2_IMAGE_1}})

| **{{SCREEN_2_NAME}}** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: {{COLOR_HEX}} | [None] |
| 2 | {{FIELD_NAME}} | {{TYPE}} | {{REQUIRE}} | {{TARGET}} |
| N | {{FIELD_NAME}} | {{TYPE}} | {{REQUIRE}} | {{TARGET}} |

## 2.N. {{SCREEN_N_NAME}}

![{{SCREEN_N_NAME}}]({{SCREEN_N_IMAGE_1}})

| **{{SCREEN_N_NAME}}** | | | | |
|---|---|---|---|---|
| **No.** | **Field name** | **Type** | **Require** | **Target** |
| 1 | Background | Background | Background: {{COLOR_HEX}} | [None] |
| N | {{FIELD_NAME}} | {{TYPE}} | {{REQUIRE}} | {{TARGET}} |
