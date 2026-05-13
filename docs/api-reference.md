# API Reference

## Core

### FeishuClient

::: feishu_kit.core.client.FeishuClient
    options:
      show_source: false
      members:
        - __init__
        - request
        - upload
        - close

### ClientPool

::: feishu_kit.core.pool.ClientPool
    options:
      show_source: false
      members:
        - __init__
        - add
        - get
        - close_all

### Exceptions

::: feishu_kit.core.exceptions.FeishuKitError
    options:
      show_source: false

::: feishu_kit.core.exceptions.AuthenticationError
    options:
      show_source: false

::: feishu_kit.core.exceptions.RateLimitError
    options:
      show_source: false

::: feishu_kit.core.exceptions.APIError
    options:
      show_source: false

## Modules

### WikiService

::: feishu_kit.modules.wiki.service.WikiService
    options:
      show_source: false

### DriveService

::: feishu_kit.modules.drive.service.DriveService
    options:
      show_source: false

### MessagingService

::: feishu_kit.modules.messaging.service.MessagingService
    options:
      show_source: false

### ContactsService

::: feishu_kit.modules.contacts.service.ContactsService
    options:
      show_source: false

### CalendarService

::: feishu_kit.modules.calendar.service.CalendarService
    options:
      show_source: false

### TaskService

::: feishu_kit.modules.task.service.TaskService
    options:
      show_source: false

### Md2FeishuService

::: feishu_kit.modules.md2feishu.service.Md2FeishuService
    options:
      show_source: false

## Server

### create_app

::: server.create_app
    options:
      show_source: false

### BaseModule

::: server.base.BaseModule
    options:
      show_source: false
