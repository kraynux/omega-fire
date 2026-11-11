<!-- Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE) -->

<div align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/assets/omega-fire.png" alt="Omega-Fire" width="512">
</div>

# 󰦝 OMEGA-FIRE

**Trạm quản lý thống nhất bảo mật mạng**

> Được phát triển bởi [kraynux](https://github.com/kraynux) cho [Omega-Server](https://kraynux.snake-mackarel.ts.net)   

Trang chính thức: [OMEGA-FIRE](https://kraynux.snake-mackarel.ts.net/omega-fire/) &nbsp; Xem trước: [Ảnh chụp màn hình](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/)  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../../LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux-informational.svg)](https://www.linux.org/)
[![Interface](https://img.shields.io/badge/Interface-Textual%20TUI-cyan.svg)](https://github.com/Textualize/textual)

🌐 Tài liệu, bản xuất & giao diện có sẵn bằng **17 ngôn ngữ** — xem [Ngôn ngữ giao diện](#ngôn-ngữ-giao-diện).  
**Ngôn ngữ:**
<img src="https://flagcdn.com/w20/fr.png" alt="France" style="height:14px;"> [Français](../../../README.md) · <img src="https://flagcdn.com/w20/gb.png" alt="English" style="height:14px;"> [English](../en/README.md) · <img src="https://flagcdn.com/w20/es.png" alt="Español" style="height:14px;"> [Español](../es/README.md) · <img src="https://flagcdn.com/w20/br.png" alt="Português (Brasil)" style="height:14px;"> [Português (Brasil)](../pt-BR/README.md) · <img src="https://flagcdn.com/w20/it.png" alt="Italiano" style="height:14px;"> [Italiano](../it/README.md) · <img src="https://flagcdn.com/w20/de.png" alt="Deutsch" style="height:14px;"> [Deutsch](../de/README.md) · <img src="https://flagcdn.com/w20/nl.png" alt="Nederlands" style="height:14px;"> [Nederlands](../nl/README.md) · <img src="https://flagcdn.com/w20/pl.png" alt="Polski" style="height:14px;"> [Polski](../pl/README.md) · <img src="https://flagcdn.com/w20/ru.png" alt="Русский" style="height:14px;"> [Русский](../ru/README.md) · <img src="https://flagcdn.com/w20/cn.png" alt="中文" style="height:14px;"> [中文](../zh-CN/README.md) · <img src="https://flagcdn.com/w20/vn.png" alt="Tiếng Việt" style="height:14px;"> [Tiếng Việt](README.md) · <img src="https://flagcdn.com/w20/th.png" alt="ไทย" style="height:14px;"> [ไทย](../th/README.md) · <img src="https://flagcdn.com/w20/id.png" alt="Bahasa Indonesia" style="height:14px;"> [Bahasa Indonesia](../id/README.md) · <img src="https://flagcdn.com/w20/jp.png" alt="日本語" style="height:14px;"> [日本語](../ja/README.md) · <img src="https://flagcdn.com/w20/kr.png" alt="한국어" style="height:14px;"> [한국어](../ko/README.md) · <img src="https://flagcdn.com/w20/in.png" alt="हिन्दी" style="height:14px;"> [हिन्दी](../hi/README.md) · <img src="https://flagcdn.com/w20/ae.png" alt="العربية" style="height:14px;"> [العربية](../ar/README.md)

---

**Omega-Fire** là một ứng dụng TUI (Terminal User Interface) viết bằng Python, xây dựng với [Textual](https://github.com/Textualize/textual). Từ một terminal, nó cung cấp một giao diện duy nhất để quản trị tường lửa Linux, Fail2Ban, các địa chỉ bị cấm, quy tắc mạng, nhật ký và thống kê hệ thống.

Giao diện Textual là chế độ hoạt động mặc định, điều hướng bằng menu, biểu mẫu được xác thực (mọi trường bắt buộc đều được kiểm tra trước khi tiếp tục) và các màn hình riêng, với chủ đề, trợ giúp theo ngữ cảnh và phím tắt dùng chung với phần còn lại của bộ OMEGA (omega-check, omega-deep, omega-stress...). Giao diện [Rich](https://github.com/Textualize/rich) cũ, tuần tự và điều khiển bằng cách nhập số, vẫn có sẵn qua `--legacy-cli` (xem [Khởi chạy](#khởi-chạy)). 
Xem trước: [Ảnh chụp màn hình](https://kraynux.snake-mackarel.ts.net/omega-fire/screenshots/index-2.html)

<p align="center">
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/translation/vi/omega-fire/A.png" width="24%" />
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/translation/vi/omega-fire/B.png" width="24%" />
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/translation/vi/omega-fire/C.png" width="24%" />
  <img src="https://raw.githubusercontent.com/kraynux/kraynux/refs/heads/main/docs/translation/vi/omega-fire/D.png" width="24%" />
</p>

Dự án được thiết kế theo các nguyên tắc của **Clean Architecture**, với sự tách biệt rõ ràng giữa miền nghiệp vụ, điều phối, hạ tầng và giao diện người dùng.

## Mục lục

- [Giới thiệu](#giới-thiệu)
- [Tính năng](#tính-năng)
- [Kiến trúc](#kiến-trúc)
- [Yêu cầu](#yêu-cầu)
- [Cài đặt](#9-cài-đặt)
- [Sử dụng](#sử-dụng)
- [Cấu hình](#cấu-hình)
- [Backend và khả năng tương thích](#backend-và-khả-năng-tương-thích)
- [Lưu trữ, nhật ký và xuất dữ liệu](#lưu-trữ-nhật-ký-và-xuất-dữ-liệu)
- [Bảo mật](#bảo-mật)
- [Kiểm thử và chất lượng](#kiểm-thử-và-chất-lượng)
- [Tình trạng dự án](#tình-trạng-dự-án)
- [Gỡ cài đặt](#gỡ-cài-đặt)
- [Giấy phép](#giấy-phép)

---

## Giới thiệu

Omega-Fire hoạt động như một **trạm điều khiển cục bộ** cho bảo mật mạng. Nó tự động phát hiện các thành phần có trên máy và điều chỉnh menu theo các khả năng thực sự có sẵn.

### Mục tiêu

- Tập hợp nftables, iptables, ip6tables và Fail2Ban trong một giao diện nhất quán.
- Giúp dễ dàng quan sát và thao tác trên các kết nối, lệnh cấm và sự kiện hệ thống.
- Tập trung việc xuất dữ liệu, sao lưu, kiểm toán và lịch sử thao tác.
- Duy trì một kiến trúc có thể kiểm thử và mở rộng.
- Hoạt động ở chế độ suy giảm khi thiếu một thành phần tùy chọn.

### Omega-Fire làm gì

- Phát hiện các backend, dịch vụ, kernel và công cụ có sẵn.
- Quản trị nftables, iptables và ip6tables khi các thành phần này có mặt.
- Quản lý các IP bị cấm, riêng lẻ hoặc theo lô, với nhập, xuất, đồng bộ và flush.
- Tạo, liệt kê và xóa các quy tắc nâng cao.
- Áp dụng các chính sách định sẵn với sao lưu tự động trước đó.
- Quản trị các jail của Fail2Ban và các lệnh cấm của chúng.
- Phân tích nhật ký trực tiếp hoặc dưới dạng thống kê.
- Cung cấp giám sát dưới dạng monitoring.
- Dùng conntrack để hiển thị các kết nối đang hoạt động khi có sẵn.
- Tạo bản xuất JSON, TXT và HTML.
- Sao lưu và khôi phục toàn bộ trạng thái trong các tệp lưu trữ `.tar.gz`.
- Ghi lại các thao tác vào nhật ký ứng dụng và một bản kiểm toán JSON có cấu trúc.
- Giám sát các dịch vụ và ứng dụng được phát hiện: systemd, runit, OpenRC, Docker, máy chủ, VNC, v.v.

### Những gì dự án không làm

- Không thay thế nftables, iptables hay Fail2Ban.
- Không phải là một tường lửa độc lập tách khỏi hệ thống.
- Không cung cấp xác thực nhiều người dùng.
- Không mở API mạng khi hoạt động bình thường.
- Không phải là dashboard web.
- Không trực tiếp bảo vệ một máy từ xa từ một máy khác.
- Theo mặc định, không cài bất kỳ tệp nào ra ngoài thư mục của chính nó.
- Không bảo đảm mọi backend đều có trên mọi bản phân phối.

---

## Tính năng

### 1. Khả năng và chẩn đoán

- Hiển thị sổ đăng ký các khả năng được phát hiện.
- Xem chi tiết một khả năng theo mã định danh.
- Quét lại hệ thống thủ công sau khi cài một thành phần.
- Xem các chẩn đoán gần đây.
- Xem và tìm kiếm trong nhật ký ứng dụng.
- Xuất trạng thái và chẩn đoán ra JSON, TXT hoặc HTML.
- Danh mục **Bộ omega**: omega-serv (các phiên bản được phát hiện và đang chạy), omega-waf (đã bật phần mở rộng `magnet`) và omega-jail (các jail đã cài đặt), hiển thị trong sổ đăng ký, dashboard và các báo cáo.

### 2. Quản lý IP thống nhất

Blacklist thống nhất cho phép làm việc với nftables và iptables từ cùng một màn hình.

- Cấm một IP hoặc một danh sách IP.
- Gỡ cấm riêng lẻ hoặc theo lô.
- Nhập trực tiếp hoặc nhập từ tệp.
- Danh sách theo backend hoặc góc nhìn thống nhất.
- Đồng bộ giữa các backend NFTables/IPTables.
- Xuất và nhập lại danh sách.
- Dọn sạch hoàn toàn một hoặc nhiều backend.
- Hỗ trợ IPv4 và IPv6.
- Quản lý các tệp blocklist (`var/blocklist/`) và các mục ghim của chúng ngay từ màn hình riêng; các tệp được đề xuất mặc định, `blocklist.txt` và `blocklist-f2b.txt`, được tạo rỗng ở lần khởi chạy đầu tiên.

### 3. Quản lý quy tắc và chính sách

- Trình hướng dẫn từng bước để tạo một quy tắc nâng cao.
- Danh sách quy tắc hệ thống và quy tắc do Omega-Fire tạo.
- Xóa một quy tắc bằng cách chọn.
- Tự động dọn các quy tắc không hoạt động trong cơ sở tham chiếu.
- Dọn dẹp và đồng bộ lại cơ sở dữ liệu với tường lửa thực tế, có xem trước và sao lưu trước, không bao giờ sửa đổi chính tường lửa.
- Quy tắc của các công cụ khác (UFW, Tailscale, Docker…) được nhận diện theo nguồn gốc: hiển thị để tham khảo, không bao giờ bị xóa từ Omega-Fire.
- Biện pháp bảo vệ trước khi áp dụng một chính sách hoặc xóa sạch iptables khi các công cụ khác có quy tắc trong đó: áp dụng ở mọi nơi, chỉ trên nftables, hoặc hủy — hệ quả được mô tả chi tiết trong phần trợ giúp.
- Áp dụng các chính sách định sẵn.
- Sao lưu tự động trước khi áp dụng một chính sách.
- Tùy chỉnh, lưu và khôi phục một chính sách.
- Nhận diện chính sách đang hoạt động trong menu trạng thái và dashboard.
- Đánh dấu các hồ sơ đã sửa dưới dạng `Hồ sơ + CUSTOM`.
- Quản lý bảng (menu 3.5): chẩn đoán chỉ đọc theo từng backend (sự hiện diện của bảng, các chính sách input/output/forward, số quy tắc) kèm giải thích các chính sách khác nhau giữa các backend (tác động thực tế, nguyên nhân và cách khắc phục).
- Khởi tạo một bảng nftables ở lần dùng đầu tiên, không bao giờ ghi đè một chain đã cấu hình.
- Đặt lại chính sách chain về ACCEPT trên một backend, để sửa một chính sách hạn chế mồ côi do một hồ sơ trước đó để lại.
- Làm trống có chọn lọc một backend hoặc làm trống đồng bộ mọi backend được phát hiện trong một thao tác.
- Xóa hoàn toàn một bảng nftables (thao tác nâng cao, ngoài các quy tắc riêng lẻ).

### 4. Quản lý Fail2Ban

- Trạng thái chi tiết của các jail và tham số của chúng.
- Số IP bị cấm và thông tin rate-limit.
- Tìm một IP trong các jail.
- Ban và unban riêng lẻ hoặc nhiều.
- Chuyển IP giữa các jail, backend và tệp.
- Tạo jail tùy chỉnh có hướng dẫn.
- Các mẫu jail định sẵn, có thể sửa và xóa.
- Nguồn gốc của từng jail: Omega-Fire, omega-jail, cấu hình chính của fail2ban hoặc tệp khác.
- Xóa jail một cách đáng tin cậy, bất kể tên tệp của nó: cảnh báo với jail do omega-jail cài đặt, từ chối có giải thích với jail trong `jail.local` hoặc trong tệp dùng chung, không bao giờ xóa các bộ lọc chuẩn của fail2ban.
- Làm trống một jail hoặc dọn sạch toàn bộ.
- Xuất ra JSON, TXT hoặc HTML.
- Kiểm tra và kiểm toán cấu hình.
- Điều khiển dịch vụ: trạng thái, khởi động, dừng, khởi động lại, bật và tắt khi khởi động máy; sau khi khởi động hoặc dừng, sổ đăng ký khả năng và dashboard được cập nhật.

### 5. Nhật ký và bảo trì

- **Thư viện nhật ký** (5.1): tự động nhập nhật ký của các phiên bản omega-serv được phát hiện, bao gồm cả nhật ký của omega-waf, ghim thủ công một đường dẫn, và lấy nhật ký từ xa qua SSH (khóa hoặc agent, không bao giờ dùng mật khẩu).
- **Yêu thích** (5.2): kết hợp các nhật ký từ Thư viện, lưu chúng dưới một tên kèm trình xem và khởi chạy trực tiếp.
- **Xem nhật ký** (5.3): một nhật ký không cần cấu hình, với trình xem tùy chọn — Đơn giản (dashboard thời gian thực: trạng thái HTTP gồm từ chối 403 và 429, Top 5 IP, đường dẫn được gọi và đường dẫn trả về 404, giống omega-log), Cổ điển (các dòng cuối rồi theo dõi trực tiếp) hoặc `lnav`.
- **Thư viện cung cấp nguồn cho mọi lựa chọn nhật ký**: 5.4, 5.5, 5.6, cũng như 8.5 và 8.6, đưa nó lên đầu danh sách, trước các mục ghim.
- Tích hợp `lnav`: nhiều nhật ký được gộp thành một góc nhìn theo thời gian duy nhất, được bọc trong header/footer của Omega-Fire (xem [Điều hướng](#điều-hướng)).
- Phân tích các IP xuất hiện nhiều nhất bằng Top N (5.4), có thể xuất ra để nạp lại vào việc dọn dẹp có mục tiêu; tìm một IP cụ thể trong toàn bộ tệp và gỡ trực tiếp IP đã chọn, không làm treo giao diện.
- Dọn dẹp có mục tiêu một hoặc nhiều IP trong tệp LOG hoặc TXT, nhập tay hoặc đánh dấu từ một bản xuất.
- Tệp được ghim với **preset để đánh dấu**: chỉ đề xuất các đường dẫn thông dụng thực sự có trên máy.
- Xoay vòng và sao lưu tức thì hoặc theo lịch, **thực sự chạy mỗi đêm** (timer systemd chạy dưới quyền root, nếu không thì một dòng trong crontab của root), kèm số bản sao lưu được giữ lại, bản sao lưu gần nhất và lần tiếp theo.
- Khôi phục một bản sao lưu.
- Dọn theo độ cũ, hạn mức, loại hoặc chọn thủ công.
- Dọn nâng cao theo thư mục hoặc môi trường.
- Thống kê 24 giờ, 7 ngày hoặc 30 ngày (5.10, xem nhanh).
- Phân tích các sự kiện, biến động, hạn mức và IP có trong các jail.

### 6. Xuất dữ liệu và báo cáo

Các định dạng có sẵn:

- **JSON**: dữ liệu có cấu trúc, tái sử dụng được.
- **TXT**: định dạng thô hoặc phù hợp để nạp vào.
- **HTML**: báo cáo dễ đọc và trực quan.

Các báo cáo có sẵn:

- Blacklist đầy đủ.
- Ruleset có cấu trúc.
- Quy tắc chọn theo nguồn gốc: hệ thống, Omega-Fire hoặc đang hoạt động.
- Báo cáo kiểm toán đầy đủ.
- Thống kê Fail2Ban.
- Trạng thái và chẩn đoán hệ thống.
- Báo cáo thống kê 7 hoặc 30 ngày.
- Bảng xếp hạng Top N các IP.
- **Thống kê nhật ký** (6.5): cùng báo cáo như omega-serv và omega-log (tổng quan, trạng thái HTTP, IP hàng đầu, đường dẫn được gọi, đường dẫn trả về 404, phân bố theo giờ, xu hướng theo ngày), chỉ nhật ký; các lệnh cấm và trạng thái tường lửa vẫn nằm trong báo cáo 7 và 30 ngày.
- Hướng dẫn trợ giúp và FAQ.

**Xem tất cả bản xuất** (6.6): mọi tệp đã xuất ở cùng một nơi, kèm loại, ngày và kích thước; báo cáo HTML mở trong trình duyệt web mặc định của người dùng, tệp JSON hoặc TXT đọc ngay trong Omega-Fire, không cần terminal hay trình quản lý tệp.

Chủ đề HTML:

- `omega-base` — xanh đêm và cyan, chủ đề mặc định.
- `omega-burn` — than hồng đỏ cam.
- `omega-neon` — cyberpunk cyan và magenta.
- `light-basic` — sáng và giản dị.
- `light-alt` — giấy màu kem và xanh rừng.

Ngôn ngữ bản xuất: đặt riêng trong cài đặt (mặc định « Giống giao diện »), để gửi báo cáo bằng ngôn ngữ của người đọc mà không đổi ngôn ngữ giao diện.

### 7. Hệ thống và lưu trữ

- Sao lưu toàn bộ trạng thái: quy tắc, lệnh cấm nftables, lệnh cấm iptables và Fail2Ban.
- Tạo các tệp lưu trữ `.tar.gz` có dấu thời gian.
- Liệt kê và khôi phục snapshot: chỉ các quy tắc của Omega-Fire có thể tạo lại y hệt mới được đặt lại; quy tắc của các công cụ khác không bao giờ bị động đến.
- Lịch sử thao tác.
- Lọc và dọn lịch sử.
- Tải lại cấu hình và quét lại mà không cần khởi động lại.

### 8. Giám sát và thống kê

- Dashboard thời gian thực, làm mới định kỳ (mỗi 2 giây), không chặn giao diện trong khi thu thập.
- Hiển thị chính sách đang hoạt động.
- Kết nối đang hoạt động qua conntrack.
- Lưu lượng, sự kiện, thống kê và nhật ký máy chủ.
- Báo cáo tổng hợp 7 và 30 ngày.
- Xuất HTML các snapshot và báo cáo.

### 9. Cài đặt

- Chọn chủ đề đang dùng trong mười chủ đề `omega-*` dùng chung với phần còn lại của bộ (xem [Chủ đề và terminal](#chủ-đề-và-terminal)), được lưu giữa hai lần chạy.
- Ghi đè thủ công hồ sơ hiển thị (tự động, đầy đủ, tiêu chuẩn, rút gọn hoặc chỉ mono), áp dụng ở lần chạy tiếp theo.
- Ngôn ngữ giao diện trong 17 ngôn ngữ (xem [Ngôn ngữ giao diện](#ngôn-ngữ-giao-diện)): chỉ giao diện khởi động lại; quy tắc tường lửa, Fail2Ban và các dịch vụ không bị ảnh hưởng.
- Ngôn ngữ của bản xuất HTML và TXT, độc lập với ngôn ngữ giao diện.
- Thư mục bản xuất và ảnh chụp màn hình có thể thay đổi, xóa sạch sau khi xác nhận.
- Truy cập từ menu chính (`9. THIẾT LẬP`) hoặc trực tiếp bằng phím `s`.

### 10. Trợ giúp

- **Hướng dẫn trợ giúp**: tất cả các trang trợ giúp được tập hợp theo thứ tự menu, mỗi trang mở được các trang liên quan.
- **FAQ**: các câu hỏi thực tế gặp phải khi sử dụng (quy tắc của công cụ khác, khôi phục, Fail2Ban, nhật ký, bản xuất và trình duyệt).
- Xuất HTML hướng dẫn và FAQ, bằng ngôn ngữ xuất.
- Phím `a` vẫn là trợ giúp của màn hình hiện tại.

---

## Kiến trúc

```text
src/omega_fire/
├── app/              Bootstrap và container tiêm phụ thuộc
├── core/             Khả năng, kiểu liệt kê và ngoại lệ
├── domain/           Logic nghiệp vụ thuần: quy tắc, IP, jail, nhật ký
├── application/      Điều phối: commands và queries
├── infrastructure/   Backend, lưu trữ, xuất dữ liệu, nhật ký và đầu dò hệ thống
├── ports/            Hợp đồng Protocol/ABC
├── interfaces/       interfaces/tui/ (Textual, mặc định) + interfaces/cli/ (Rich, --legacy-cli)
├── plugins/          Tiện ích mở rộng tích hợp: nftables, iptables, Fail2Ban, conntrack
└── shared/           Phân tích cú pháp, mạng, định dạng và tiện ích dùng chung
```

### Nguyên tắc thiết kế

- `domain/` không chứa I/O cũng như phụ thuộc vào hạ tầng.
- `application/` điều phối các ca sử dụng thông qua miền và các port — các màn hình Textual và các thao tác của giao diện Rich gọi cùng các commands/queries, logic nghiệp vụ không phụ thuộc vào giao diện nào trong hai.
- `infrastructure/` là lớp duy nhất được phép gọi `nft`, `iptables`, `fail2ban-client` và các công cụ bên ngoài khác (subprocess, pty, tệp).
- `interfaces/` không được gọi trực tiếp `subprocess`.
- `ports/` định nghĩa các hợp đồng mà adapter mong đợi.
- `core/` cung cấp sổ đăng ký khả năng được các lớp khác nhau sử dụng.
- Các plugin cho phép thêm hoặc phát triển backend mà không sửa miền nghiệp vụ.
- Giao diện Textual (`interfaces/tui/`) dựa trên [`omega-lib`](https://github.com/) (phụ thuộc dùng chung cho cả bộ OMEGA: chủ đề 9 token, phát hiện terminal, hợp đồng port chung), không phát hành trên PyPI — được đóng gói sẵn trong tệp phân phối (`vendor/omega-lib/`, xem [Cài đặt](#9-cài-đặt)).
- Mọi lời gọi có thể chậm (backend tường lửa, `fail2ban-client`, ổ đĩa) được kích hoạt từ một màn hình Textual đều chạy nền (thread), không bao giờ trên thread chính của giao diện — dashboard hay biểu mẫu vẫn phản hồi trong suốt thao tác thay vì làm đơ cả ứng dụng.

### Cấu trúc dữ liệu

Omega-Fire dùng SQLite thông qua thư viện chuẩn `sqlite3`, không dùng ORM bên ngoài. Các tập dữ liệu chính liên quan đến lệnh cấm, quy tắc, sự kiện kiểm toán và snapshot.

Các migration được đánh phiên bản và tự động áp dụng khi khởi động.

---

## Yêu cầu

### Hệ thống

- Linux, ưu tiên Arch Linux và các bản phân phối tương thích.
- Python 3.10 trở lên.
- Quyền root có sẵn qua `sudo`.
- Một trình quản lý dịch vụ: systemd, runit hoặc OpenRC.
- Ít nhất một backend tường lửa: nftables hoặc iptables.
- Một terminal tối thiểu 80x24 (xem [Chủ đề và terminal](#chủ-đề-và-terminal) để biết chi tiết các hồ sơ hiển thị theo kích thước có sẵn).

### Phụ thuộc Python

Các phụ thuộc vận hành được định nghĩa trong `requirements.txt`:

- `textual` — giao diện TUI mặc định.
- `omega-lib` — chủ đề, phát hiện terminal và các hợp đồng dùng chung với bộ OMEGA (không phát hành trên PyPI, xem [Kiến trúc](#kiến-trúc) và [Cài đặt](#9-cài-đặt)).
- `rich` — hiển thị giao diện `--legacy-cli` và một số báo cáo.
- `psutil` — thông tin hệ thống (CPU, bộ nhớ, mạng, tiến trình) cho dashboard và chẩn đoán.
- `jinja2` — tạo các bản xuất HTML.
- `python-dotenv` — biến môi trường.
- `pyte` — trình giả lập terminal ảo, để bọc `lnav` (menu 8.6 và trình xem lnav của 5.2 / 5.3).

Các công cụ chất lượng (`pytest`, `black`, `flake8`, `mypy`) được liệt kê dưới dạng chú thích trong `requirements.txt`: bỏ chú thích hoặc cài riêng nếu bạn đóng góp cho dự án (xem [Kiểm thử và chất lượng](#kiểm-thử-và-chất-lượng)).

### Công cụ tùy chọn khuyến nghị

Ứng dụng hoạt động ở chế độ suy giảm nếu thiếu các công cụ này:

- `fail2ban` — cấm tự động.
- `conntrack` hoặc `conntrack-tools` — kết nối đang hoạt động và thống kê mạng.
- `lnav` — phân tích nhật ký nâng cao trên nhiều tệp.

Trên Arch Linux và các bản dẫn xuất:

```bash
sudo pacman -S fail2ban conntrack-tools lnav
```

---

## Cài đặt

Tệp lưu trữ chính thức được cung cấp ở định dạng `.tar.gz`. Hãy kiểm tra tính toàn vẹn trước khi cài đặt:

```bash
sha256sum omega-fire.tar.gz
```

> ⚠️ **Ba phương pháp này dành cho lần cài đặt đầu tiên.** Nếu `~/omega-fire` đã tồn tại (cập nhật từ phiên bản trước), hãy dùng phần [Cập nhật](#cập-nhật) bên dưới — đừng bao giờ chạy lại các lệnh này từ bên trong một thư mục `omega-fire` đã có: `tar` sẽ cố tạo một `omega-fire/omega-fire/` lồng nhau và thất bại với lỗi quyền nếu thư mục đó thuộc về root (thường gặp nếu lần giải nén trước vô tình dùng `sudo tar`).

### Phương pháp 1 — script cài đặt

```bash
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Có vẻ bạn đã ở trong một thư mục omega-fire — xem phần Cập nhật trong README." >&2; exit 1; }
[ -d omega-fire ] && echo "ℹ️ Đã giải nén ở đây, bỏ qua bước này." || tar -xzf omega-fire.tar.gz
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire đã tồn tại, bỏ qua việc di chuyển." || mv omega-fire ~/
cd ~/omega-fire/
chmod +x install.sh
./install.sh
```

Khởi chạy:

```bash
./omega-fire.sh
```

Nếu alias đã được cài, hãy mở một terminal mới rồi dùng:

```bash
fire
```

### Phương pháp 2 — cài đặt đầy đủ bền vững

Lệnh này có thể chạy lại: nó bỏ qua các bước đã thực hiện.

```bash
([ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Có vẻ bạn đã ở trong một thư mục omega-fire — xem phần Cập nhật trong README." >&2; exit 1; }; [ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire đã tồn tại, bỏ qua việc giải nén." || (tar -xzf omega-fire.tar.gz && mv omega-fire ~/)) && cd ~/omega-fire/ && ([ -d .venv ] && echo "ℹ️ .venv đã tồn tại, bỏ qua bước này." || python3 -m venv .venv) && source .venv/bin/activate && ([ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib || true) && pip install -r requirements.txt && chmod +x omega-fire.sh && mkdir -p var && (getent group omega-fire >/dev/null 2>&1 && echo "ℹ️ Nhóm omega-fire đã có." || sudo groupadd omega-fire) && (groups "$USER" 2>/dev/null | grep -qw omega-fire && echo "ℹ️ $USER đã là thành viên nhóm omega-fire." || sudo usermod -aG omega-fire "$USER") && sudo chgrp -R omega-fire var && sudo chmod -R 2775 var && echo "✅ Đã cài Omega-Fire. Chạy ./omega-fire.sh."
```

### Phương pháp 3 — cài đặt chi tiết

```bash
# 0. Kiểm tra rằng không chạy lại từ bên trong một omega-fire đã có
[ "$(basename "$PWD")" = "omega-fire" ] && { echo "❌ Có vẻ bạn đã ở trong một thư mục omega-fire — xem phần Cập nhật trong README." >&2; exit 1; }

# 1. Giải nén
[ -d omega-fire ] && echo "ℹ️ Đã giải nén ở đây, bỏ qua bước này." || tar -xzf omega-fire.tar.gz

# 2. Di chuyển vào thư mục home
[ -d ~/omega-fire ] && echo "ℹ️ ~/omega-fire đã tồn tại, bỏ qua việc di chuyển." || mv omega-fire ~/

# 3. Vào thư mục dự án
cd ~/omega-fire/

# 4. Tạo môi trường ảo
[ -d .venv ] && echo "ℹ️ .venv đã tồn tại, bỏ qua việc tạo." || python3 -m venv .venv

# 5. Cài các phụ thuộc (omega-lib đóng gói sẵn, nếu có, trước requirements.txt)
source .venv/bin/activate
[ -d vendor/omega-lib ] && pip install -q -e vendor/omega-lib
pip install -r requirements.txt

# 6. Cấp quyền thực thi cho trình khởi chạy
chmod +x omega-fire.sh

# 7. Chuẩn bị var/ cho root và người dùng hiện tại
mkdir -p var
getent group omega-fire >/dev/null 2>&1 || sudo groupadd omega-fire
groups "$USER" 2>/dev/null | grep -qw omega-fire || sudo usermod -aG omega-fire "$USER"
sudo chgrp -R omega-fire var
sudo chmod -R 2775 var

# 8. Khởi chạy
./omega-fire.sh
```

`vendor/omega-lib/` chỉ có trong tệp lưu trữ chính thức (`build-release.sh` tự động đưa nó vào, vì omega-lib không phát hành trên PyPI); trong bản clone phát triển, hãy cài nó riêng từ kho của chính nó (`pip install -e duong/dan/toi/omega-lib`).

Nhóm riêng và bit `setgid` cho phép root và người dùng chia sẻ các tệp tạo ra trong `var/` mà không mở quyền cho toàn hệ thống. Có thể cần đăng nhập lại hoặc chạy `newgrp omega-fire` để được hưởng ngay tư cách thành viên nhóm.

### Cập nhật

Nếu `~/omega-fire` đã tồn tại (lần cài trước), **đừng bao giờ chạy lại các lệnh cài đặt từ bên trong thư mục này**: `tar` sẽ cố tạo một `omega-fire/omega-fire/` lồng nhau và thất bại, thường kèm một loạt lỗi « Quyền bị từ chối » nếu thư mục thuộc về `root` (thường gặp nếu lần giải nén trước vô tình dùng `sudo tar`).

Quy trình khuyến nghị, từ bất kỳ thư mục nào **ngoài `~/omega-fire`** (thường chính là `~`):

```bash
# 1. Kiểm tra trạng thái và chủ sở hữu của bản cài hiện có
ls -ld ~/omega-fire

# 2. Để riêng bản cài cũ thay vì ghi đè lên nó
sudo mv ~/omega-fire ~/omega-fire.old-$(date +%Y%m%d)

# 3. Giải nén tệp lưu trữ mới trực tiếp vào thư mục home
tar -xzf omega-fire.tar.gz -C ~/

# 4. Cài lại (tạo lại venv, cài lại phụ thuộc, đặt lại quyền của var/)
cd ~/omega-fire
chmod +x install.sh
./install.sh

# 5. Khởi chạy
./omega-fire.sh
```

Bước 4 (`./install.sh`) tự động nhận ra tình huống này (cơ sở dữ liệu `var/db/` không có ở đây, thư mục `~/omega-fire.old-YYYYMMDD` được tìm thấy ngay bên cạnh) và **tự lấy lại** `config/omega-fire.conf`, cơ sở dữ liệu, blocklist, các bản sao lưu, bản xuất và ảnh chụp màn hình từ bản cài cũ — không hỏi, không cần bước thủ công. Không cần làm gì thêm ngoài các điểm 1 đến 5 ở trên, bất kể bản cài trước của bạn chứa gì.

Nếu có nhiều thư mục giống bản cài cũ nằm cạnh nhau (mơ hồ), `install.sh` không đoán gì cả: nó hiển thị đường dẫn của chúng và mời bạn tự chạy `sudo ./migrate-state.sh <thư-mục>` khi đã xác định đúng nguồn.

Sau khi xác nhận bản cài mới, có thể xóa thư mục cũ `~/omega-fire.old-YYYYMMDD` (`sudo rm -rf ~/omega-fire.old-YYYYMMDD`).

### Alias Bash hoặc Zsh

```bash
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.bashrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.bashrc
grep -qxF 'alias fire="sudo ~/omega-fire/omega-fire.sh"' ~/.zshrc 2>/dev/null || echo 'alias fire="sudo ~/omega-fire/omega-fire.sh"' >> ~/.zshrc
```

Sau đó tải lại shell:

```bash
source ~/.bashrc 2>/dev/null || source ~/.zshrc
```

### Biểu tượng và ký hiệu Nerd Fonts

Nếu biểu tượng không hiển thị, hãy cài các ký hiệu Nerd Fonts:

```bash
mkdir -p ~/.local/share/fonts
curl -fLo /tmp/NerdFontsSymbolsOnly.zip \
  https://github.com/ryanoasis/nerd-fonts/releases/latest/download/NerdFontsSymbolsOnly.zip
unzip -o /tmp/NerdFontsSymbolsOnly.zip -d ~/.local/share/fonts
fc-cache -fv
```

---

## Sử dụng

### Khởi chạy

```bash
cd ~/omega-fire
./omega-fire.sh

# hoặc đơn giản, nếu đã tạo alias:
fire
```

Trình khởi chạy:

1. Kiểm tra quyền root và chạy lại qua `sudo` nếu cần.
2. Phát hiện `.venv`, `venv` hoặc Python của hệ thống.
3. Cấu hình `PYTHONPATH` trỏ tới `src/`.
4. Chạy `python -m omega_fire` — giao diện **Textual**, theo mặc định.

Để chạy giao diện Rich cũ (nhập số tuần tự) thay thế:

```bash
./omega-fire.sh --legacy-cli
```

**Giao diện Rich cũ không còn được phát triển, nhưng vẫn có thể sử dụng.** Giao diện cũ vẫn là giao diện của phiên bản 3.0, bằng tiếng Pháp: menu 5 gốc (không có Thư viện, Yêu thích hay trình xem Cổ điển), không có "Xem tất cả bản xuất", không có hướng dẫn trợ giúp hay FAQ, không có preset. Giao diện Textual mang phiên bản 3.5 đầy đủ.

### Ngôn ngữ giao diện

17 ngôn ngữ: tiếng Pháp, tiếng Anh, tiếng Tây Ban Nha, tiếng Bồ Đào Nha (Brazil), tiếng Ý, tiếng Đức, tiếng Hà Lan, tiếng Ba Lan, tiếng Nga, tiếng Trung, tiếng Việt, tiếng Thái, tiếng Indonesia, tiếng Nhật, tiếng Hàn, tiếng Hindi, tiếng Ả Rập. Chọn trong cài đặt (phím `s`, « Langue / Language », nhãn không bao giờ được dịch), áp dụng bằng cách chỉ khởi động lại giao diện, hoặc dùng một lần `OMEGA_FIRE_LANG=vi ./omega-fire.sh` (trình khởi chạy giữ biến này qua `sudo`). Trong console văn bản Linux (TTY), các ngôn ngữ có chữ viết không có trong phông chữ console (tiếng Việt, tiếng Trung, tiếng Thái, tiếng Nhật, tiếng Hàn, tiếng Hindi, tiếng Ả Rập) được hiển thị bằng tiếng Anh trong phiên đó. Tiếng Ả Rập hiển thị từ phải sang trái. Với tiếng Hindi, Terminator, GNOME Terminal, Xfce Terminal và Alacritty hiển thị văn bản thẳng hàng; các terminal tự ghép chữ nối (Kitty, Ghostty, Konsole) có thể làm lệch khung và cột. **Ngôn ngữ bản xuất** (báo cáo HTML và TXT) được đặt riêng, mặc định « Giống giao diện ». Nhật ký ứng dụng và lịch sử kiểm tra vẫn được ghi bằng tiếng Pháp; tiêu đề trong lịch sử được hiển thị bằng ngôn ngữ đã chọn. Giao diện cũ (`--legacy-cli`) vẫn bằng tiếng Pháp.

### Liên hệ và hỗ trợ

Phần trợ giúp (phím `a`) có màn hình **Liên hệ và hỗ trợ**: *Mời một ly cà phê* (trang PayPal của nhà phát triển), *Liên hệ hỗ trợ* (địa chỉ email và biểu mẫu liên hệ của trang web, hiển thị rõ ràng), *Khai báo là người dùng (ẩn danh)* và *Kiểm tra cập nhật*. Việc khai báo là tự nguyện, tắt theo mặc định và chỉ gửi một lần: nó chỉ dùng để đếm số người dùng và, nếu bạn muốn, châu lục hoặc quốc gia của họ (danh sách đóng, không bao giờ là văn bản tự do). Nó gửi một khóa được tạo ngẫu nhiên, tên phần mềm (`omega-fire`) và phiên bản của nó; không bao giờ gửi tên, tên máy, thiết lập, mục tiêu hay kết quả. Địa chỉ IP không được lưu trong các khai báo, nhưng, như mọi lượt truy cập, nó đi qua các kiểm tra bảo mật và nhật ký của máy chủ nhận. Có thể rút lại bất cứ lúc nào từ cùng màn hình (*Không khai báo tôi nữa*). Việc kiểm tra cập nhật chỉ đọc danh sách các phiên bản đã phát hành trên trang web, và không bao giờ khi chưa nhấp.

### Luồng chung

1. Màn hình khởi động (splash), sau đó là cảnh báo nếu terminal quá nhỏ.
2. Phát hiện khả năng hệ thống (màn hình riêng, không chặn).
3. Menu chính: 8 mục theo chủ đề (1-8), cài đặt (9) và trợ giúp (10).
4. Chọn một mục, rồi một thao tác — mỗi thao tác mở một biểu mẫu mà mọi trường bắt buộc đều được xác thực trước khi tiếp tục.
5. Xác nhận rõ ràng trước mọi thao tác nhạy cảm hoặc phá hủy (flush, dọn sạch, khôi phục...).
6. Chạy nền cho các thao tác chậm (giao diện vẫn dùng được trong lúc chờ), rồi quay lại menu với bản tóm tắt kết quả.

### Điều hướng

- Mũi tên lên/xuống: di chuyển con trỏ trong danh sách hoặc menu.
- Tab / Shift+Tab: di chuyển giữa các trường của biểu mẫu.
- Enter: chọn hoặc xác nhận.
- Nhấp vào một dòng của bảng: chọn dòng đó và điền sẵn các trường liên quan (nguồn cần ghim, jail đích, v.v.).
- `Esc`: quay lại màn hình trước (hỏi xác nhận thoát khi ở màn hình chính).
- `a`: trợ giúp theo ngữ cảnh — mô tả chi tiết hành động hiện tại, hoặc toàn bộ hành động của mục hiện tại nếu chưa mở màn hình hành động nào; hướng dẫn đầy đủ và FAQ nằm ở menu 10.
- `t`: chuyển sang chủ đề tiếp theo, không cần xác nhận.
- `r`: phát hiện lại kích thước và họ terminal.
- `s`: mở cài đặt (chủ đề, hồ sơ hiển thị, ngôn ngữ, thư mục).
- `q` / `Ctrl+Q`: thoát, có xác nhận.

#### Đặc điểm của màn hình lnav (8.6, và trình xem lnav của 5.2 / 5.3)

`lnav` được bọc trong một pseudo-terminal với header/footer Omega-Fire cố định quanh góc nhìn riêng của nó, để tránh mọi xung đột giữa phím tắt gốc của nó và của Omega-Fire:

- Mũi tên ↑↓: điều hướng trong nhật ký (phím tắt gốc của `lnav`, được chuyển nguyên).
- Mũi tên ←→: cuộn ngang trên các dòng dài (phím tắt gốc của `lnav`).
- `g` / `G`: tới đầu / cuối (phím tắt gốc của `lnav`).
- `Ctrl+C`: đánh dấu dòng hiện tại và sao chép vào bộ nhớ tạm của hệ thống (thay cho lệnh sao chép gốc của `lnav`, có thể bị treo trên một số hệ thống).
- `t` thường: chủ đề tiếp theo, riêng cho góc nhìn này (`T` hoa vẫn là phím tắt gốc của `lnav` để hiển thị thời gian giữa các dòng).
- `Ctrl+Q`: quay lại Omega-Fire (đóng `lnav` gọn gàng, không thoát ứng dụng).

---

## Chủ đề và terminal

Mười chủ đề `omega-*` được dùng chung với phần còn lại của bộ OMEGA:

```text
omega-base       omega-dark       omega-light
omega-neon       omega-burn       omega-pink
omega-hack       omega-contrast   omega-mono
omega-minimal
```

- Chuyển đổi giữa các chủ đề bằng `t`, hoặc chọn trực tiếp một chủ đề trong cài đặt (`s`).
- Chủ đề đã chọn được lưu và giữ lại ở lần chạy tiếp theo.
- Omega-Fire tự động điều chỉnh độ phức tạp hình ảnh (viền, splash, mật độ thông tin) theo terminal được phát hiện thông qua một **hồ sơ hiển thị**: Đầy đủ, Tiêu chuẩn, Rút gọn hoặc Mono (chỉ ASCII). Hồ sơ có thể được ghi đè thủ công trong cài đặt.

| Kích thước tối thiểu | Hồ sơ | Terminal tiêu biểu |
|---|---|---|
| 120×32 trở lên | Đầy đủ | Ghostty, Alacritty, WezTerm, Kitty |
| 100×28 trở lên | Tiêu chuẩn | Konsole, GNOME Terminal, Terminator, xfce4-terminal |
| 80×24 trở lên | Rút gọn | urxvt, xterm, SSH hiện đại |
| dưới 80×24 | Mono (chỉ ASCII) | Linux TTY, SSH cũ |

Dưới 80×24, việc khởi chạy bị từ chối (yêu cầu kích thước tối thiểu); hãy đổi kích thước terminal rồi chạy lại, hoặc dùng `r` sau khi đổi kích thước nếu hiển thị chưa tự cập nhật.

---

## Cấu hình

Cấu hình riêng có thể được điều chỉnh trong:

```text
omega-fire/config/omega-fire.conf
```

Nó có thể định nghĩa, trong số những thứ khác:

- đường dẫn nhật ký;
- máy chủ và nguồn giám sát;
- backend có sẵn hoặc đường dẫn tùy chỉnh;
- môi trường cần phân tích;
- các tham số phù hợp với một bản cài cụ thể.

Cấu hình được đọc lại khi khởi động lại hoặc khi quét lại thủ công (menu 1.3 hoặc 7.4).

Tệp này hoàn toàn tùy chọn (ứng dụng vẫn chạy bình thường khi không có nó, dựa vào biến môi trường) và **bị loại khỏi tệp phân phối** — một bản cập nhật không bao giờ âm thầm ghi đè lên nó, và `install.sh` tự động lấy lại nó từ bản cài cũ nếu có (xem « Cập nhật » ở trên).

### Đường dẫn nội bộ và đường dẫn hệ thống

Theo mặc định, Omega-Fire làm việc trong thư mục của chính nó:

```text
var/exports/       # thư mục nội bộ của dự án
/var/exports/      # đường dẫn tuyệt đối của hệ thống
```

Vì vậy dấu `/` ở đầu có ý nghĩa. Việc nhập và xuất ra hệ thống phải được người dùng yêu cầu rõ ràng.

---

## Backend và khả năng tương thích

Omega-Fire phát hiện các thành phần và chỉ bật những tính năng dùng được.

| Thành phần | Vai trò | Trạng thái |
|---|---|---|
| nftables | Tường lửa IPv4/IPv6 hiện đại | Khuyến nghị |
| iptables | Tường lửa IPv4 | Tương thích |
| ip6tables | Tường lửa IPv6 với iptables | Tương thích nếu có |
| Fail2Ban | Jail và cấm tự động | Tùy chọn |
| conntrack | Kết nối đang hoạt động | Tùy chọn |
| lnav | Phân tích nhật ký nâng cao | Tùy chọn |
| systemd, runit, OpenRC | Quản lý dịch vụ | Phát hiện tự động |
| Docker, VNC, máy chủ | Ứng dụng và dịch vụ được phát hiện | Tùy bản cài |

### IPv4 và IPv6

Cả hai họ địa chỉ đều được các backend tương thích hỗ trợ:

- nftables: IPv4 và IPv6 dual stack;
- iptables/ip6tables: tùy các tệp nhị phân có sẵn;
- Fail2Ban: tùy cấu hình của jail và hệ thống.

Các định dạng IPv6 dài, rút gọn, cục bộ, hỗn hợp, có số không và ký hiệu CIDR đều được các thành phần liên quan xử lý.

---

## Lưu trữ, nhật ký và xuất dữ liệu

### Lưu trữ

- SQLite qua `sqlite3`.
- Các bảng liên quan đến lệnh cấm, quy tắc, kiểm toán và snapshot.
- Migration có phiên bản, được áp dụng tự động.
- Tệp lưu trữ toàn bộ trạng thái ở định dạng `.tar.gz`.
- Các mục ghim (nguồn nhật ký yêu thích) và lịch sử gần đây được lưu bằng JSON (`var/runtime/`), vẫn còn sau khi khởi động lại.

### Nhật ký

- Nhật ký văn bản của ứng dụng: `var/logs/app.log`.
- Nhật ký kiểm toán JSON có cấu trúc, gồm `event_type`, `actor`, `action`, `result` và `details`.

### Xuất dữ liệu

Có thể xuất dữ liệu ở JSON, TXT và HTML, với nhiều chủ đề CSS cho báo cáo HTML.

---

## Bảo mật

Omega-Fire tác động lên các thành phần quan trọng của hệ thống và cần được dùng thận trọng.

- Việc khởi chạy cần quyền root qua `sudo`.
- Flush, dọn sạch toàn bộ và áp dụng một chính sách có thể mang tính phá hủy.
- Một chính sách định sẵn sẽ kích hoạt sao lưu tự động trước khi thay đổi.
- Trên iptables / ip6tables, áp dụng một chính sách hoặc xóa sạch một backend cũng xóa luôn quy tắc của các công cụ khác (UFW…): Omega-Fire báo trước và để bạn chọn trước khi thực hiện.
- Hãy sao lưu thủ công trước mỗi thay đổi lớn.
- Kiểm tra trạng thái thực tế của tường lửa, jail và kết nối sau mỗi thao tác.
- Hãy thử trước trên một máy hoặc mục tiêu dùng một lần.
- Dùng các mạng tài liệu RFC 5737 cho thử nghiệm IPv4: `192.0.2.0/24`, `198.51.100.0/24` và `203.0.113.0/24`.
- Kiểm tra các bản xuất và snapshot trước khi khôi phục chúng trên máy vận hành thật.
- Không cấp cho thư mục `var/` quyền rộng hơn mức cần thiết.

---

## Kiểm thử và chất lượng

Bộ kiểm thử gồm 137 unit test (hơn 8.000 trường hợp được kiểm tra): miền nghiệp vụ, điều phối (`application/`), hạ tầng, và các màn hình Textual được thêm hoặc sửa trong 3.5, chạy với các stylesheet thật (bố cục, luồng đầy đủ, ngôn ngữ xuất). Kho lưu trữ này không chứa thư mục `tests/`: hãy lấy nó từ kho phát triển của bạn nếu cần chạy.

```bash
source .venv/bin/activate
python -m unittest discover -s tests/unit -t .
```

Kiến trúc phân lớp tách biệt nghiêm ngặt miền nghiệp vụ khỏi phần trình bày (`domain/`, `application/`, `ports/` dưới dạng `Protocol`, xem [Kiến trúc](#kiến-trúc)): phần lớn các bài kiểm thử không cần root cũng không cần tường lửa thật.

Nếu bạn đóng góp cho dự án, hãy cài các công cụ chất lượng được khai báo (dưới dạng chú thích) trong `requirements.txt`:

```bash
pip install pytest pytest-cov black flake8 mypy
```

Các công cụ có sẵn sau khi cài:

```bash
black .
flake8 .
mypy src/
pytest --cov
```

---

## Tình trạng dự án

### Điểm đã vận hành

- TUI Textual thống nhất cho các cơ chế bảo mật mạng chính, biểu mẫu được xác thực, chủ đề và trợ giúp theo ngữ cảnh dùng chung với bộ OMEGA.
- Giao diện Rich lâu đời được giữ làm phương án dự phòng (`--legacy-cli`).
- Phát hiện khả năng tự động.
- Quản lý các backend có sẵn.
- Hỗ trợ IPv4/IPv6 tùy công cụ có mặt.
- Ghi nhật ký ứng dụng và kiểm toán.
- Sao lưu và khôi phục.
- Xuất JSON, TXT và HTML.
- Dashboard và thống kê, được làm mới nền mà không chặn giao diện.
- Kiến trúc phân lớp có tài liệu.

### Hạn chế đã biết

- Bộ kiểm thử bao phủ các màn hình Textual của 3.5, chưa bao phủ toàn bộ các màn hình cũ hơn (xem [Kiểm thử và chất lượng](#kiểm-thử-và-chất-lượng)).
- Cơ chế `ExecutionPlan`/`PipelineStep` vẫn còn một phần trong dự án.
- Mức độ có sẵn chính xác của các tính năng phụ thuộc vào tệp nhị phân, dịch vụ, quyền và cấu hình của máy chủ.
- Giao diện Rich lâu đời (`--legacy-cli`) không còn là trục phát triển chính; nó được giữ lại cho đến khi giao diện Textual hoàn toàn đáng tin cậy trong điều kiện thực tế.

---

## Gỡ cài đặt

Nếu dữ liệu vẫn nằm trong thư mục dự án:

```bash
sudo rm -rf ~/omega-fire
```

Xóa thủ công các tệp đã xuất ở nơi khác, các alias `fire` có thể đã thêm vào `~/.bashrc` hoặc `~/.zshrc`, cũng như nhóm riêng nếu không còn dùng:

```bash
sudo groupdel omega-fire
```

Chỉ chạy lệnh cuối này nếu không có tệp hay dịch vụ nào khác phụ thuộc vào nhóm này.

---

## Giấy phép

Omega-Fire được phân phối theo giấy phép **MIT**. Xem tệp [`LICENSE`](../../../LICENSE) để đọc toàn văn.

---

> **Omega-Fire — Quan sát, điều khiển, kiểm toán, bảo vệ.**
>
> Một giao diện TUI thống nhất cho nftables, iptables, ip6tables, Fail2Ban, nhật ký và giám sát mạng.
