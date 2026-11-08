# Lời thuyết trình và câu hỏi giám khảo

Mỗi đoạn được viết cho khoảng 30–45 giây ở tốc độ trình bày vừa phải. Slide 1–10 là phần chính. A1–A8 dùng khi giám khảo hỏi sâu. Các con số và vị trí nguồn nằm trong [nội dung slide](11_SLIDE_READY_CONTENT.md) và [ma trận bằng chứng](13_SLIDE_EVIDENCE_MATRIX.csv).

## 1. Checkout Credit Copilot

**Lời nói.** Em xin giới thiệu Checkout Credit Copilot, một bàn làm việc dành cho cán bộ xem xét khoản vay nhỏ tại điểm mua. Khi mở một hồ sơ, cán bộ thấy ngay nguồn bằng chứng, cách tính khả năng trả và lý do hệ thống đề xuất đường xử lý. Phiên bản hiện tại chạy trên hồ sơ mô phỏng. Bên cạnh đó, Research Lab cho phép giám khảo kiểm tra một thí nghiệm dự báo default với dữ liệu công khai và bộ kết quả có thể tái hiện.

- **COBI đã cấp khoản vay nào chưa?** MVP có chức năng ghi nhận bước duyệt và lý do. Mọi hồ sơ trình diễn đều mô phỏng.
- **Hai phần dùng cùng một mô hình không?** Workbench dùng phép tính và policy. Research Lab tải mô hình UCI với bộ đầu vào và nhãn riêng.

## 2. Checkout Lending in the Supplied HLBVN Case

**Lời nói.** Hồ sơ tình huống HLBVN mô tả thời gian ra quyết định từ 1,8 đến 4,6 ngày làm việc, với chi phí xử lý 380 nghìn đồng cho mỗi hồ sơ. Với khoản vay nhỏ, chi phí cố định và việc chuyển qua nhiều bước xác minh tạo áp lực lớn lên trải nghiệm mua hàng. Đây là số liệu của đề bài. Khi có pilot, nhóm sẽ đo lại thời gian và chi phí trên cùng phạm vi hồ sơ để có đường cơ sở so sánh.

- **Hai số đó do nhóm đo hay do đề bài cung cấp?** Đề bài cung cấp và trang 2 của bản trình bày ghi rõ phạm vi. Nhóm chưa có log vận hành độc lập.
- **23,75% có phải tỷ lệ chi phí chung?** Đó là 380.000 chia 1.600.000, khoản vay nhỏ nhất trong ví dụ của case. Không suy rộng cho toàn danh mục.

## 3. Retail Banks and Merchant Checkout Partners

**Lời nói.** Bên chịu trách nhiệm chính là ngân hàng, cụ thể là bộ phận tín dụng và quản trị rủi ro. Cán bộ dùng workbench để xem hồ sơ, xác định điểm còn thiếu và ghi lại bước tiếp theo. Đối tác bán lẻ và người mua là hai bên nhận kết quả của quy trình tại checkout. Nếu triển khai pilot, nhóm sẽ cùng ngân hàng xác định loại khoản vay và phạm vi khách hàng trước, rồi mới đánh giá giá trị cho từng nhóm.

- **Ai có quyền quyết định tín dụng?** Ngân hàng giữ quyền này. Workbench mô phỏng hỗ trợ cán bộ và ghi nhận đường xem xét.
- **Merchant đã tích hợp thật chưa?** Merchant là đối tác dự kiến trong case. Tích hợp và kết quả chuyển đổi đang ở trạng thái chưa đo.

## 4. The Document-to-Decision Bottleneck

**Lời nói.** Phân tích tình huống ban đầu cho thấy chứng từ tách rời, thông tin từ các nguồn khó đối chiếu và cán bộ phải lặp lại nhiều bước. COBI đưa dữ liệu đã có, trạng thái kiểm tra và phần tính toán vào cùng một hồ sơ. Cán bộ có thể nhận ra phần nào còn thiếu trước khi chọn đường xử lý. Giá trị của cách tổ chức này sẽ được đo bằng số lần làm lại và số phút cán bộ thực sự dành cho mỗi hồ sơ.

- **Điểm nghẽn đã được đo theo từng bước chưa?** Chưa. Trang 4 trình bày chẩn đoán của case. Pilot cần log thời gian và thao tác theo từng bước.
- **Điểm CS có chứng minh tài liệu chính xác không?** CS tổng hợp độ phủ, nhất quán, độ mới và xác minh. Chưa có nhãn lỗi độc lập để kiểm định.

## 5. Proposed Solution

**Lời nói.** COBI V2 có hai luồng. Workbench nhận hồ sơ checkout mô phỏng, chạy các điều kiện bắt buộc, tính khả năng trả và gửi một đường xem xét cho cán bộ. Research Lab dùng dữ liệu thẻ tín dụng UCI để đo hiệu năng dự báo default tháng sau. API nghiên cứu kiểm tra bộ biến, nguồn và kỳ hạn nhãn trước khi chấm. Khi yêu cầu dùng mô hình UCI cho hồ sơ checkout, hệ thống trả trạng thái không tương thích và giữ nguyên đường xử lý mô phỏng.

- **Điểm UCI có thể lọt vào routing nếu người dùng yêu cầu không?** Audit gọi thử cả hai API. Research API trả 422 với schema sai, còn mô phỏng checkout trả trạng thái không tương thích và giữ nguyên routing.
- **Hồ sơ thiếu consent đi đâu?** HOLD để cán bộ xử lý. Sau khi rút consent, việc bật lại cờ trong một kịch bản vẫn không khôi phục scoring.

## 6. How AI Helps

**Lời nói.** Phần học máy thực sự nằm trong Research Lab. Nhóm so sánh mười một cấu hình, gồm baseline theo tỷ lệ default, logistic regression, XGBoost và mạng MLP. Mười chín biến gốc thành tám mươi lăm đầu vào sau khi chuẩn hóa số tiền và mã hóa trạng thái trả nợ. XGBoost có log loss validation thấp nhất là 0,432396. Kết quả này trả lời câu hỏi nghiên cứu trên UCI. Trong workbench, các công thức và ngưỡng được hiển thị để cán bộ có thể kiểm tra.

- **Vì sao không chọn theo accuracy?** Log loss đánh giá trực tiếp chất lượng xác suất và phạt dự báo sai quá tự tin. Chưa chọn ngưỡng quyết định tín dụng.
- **Vì sao nói XGBoost thắng?** Nó tốt nhất trong lưới đã đăng ký và vượt LR 0,012352 trên validation, lớn hơn biên 0,001. Kết luận chỉ áp dụng cho thí nghiệm này.

## 7. How It Works

**Lời nói.** Hồ sơ phải qua các điều kiện về consent, danh tính mô phỏng, quyền nguồn, đối chiếu tiền mua và tính toàn vẹn của bằng chứng. Nếu vượt qua, hệ thống tính CS và khả năng trả. Sau đó mới so chi phí giả định trong các đường đủ điều kiện. Điểm rủi ro mô phỏng không quyết định đường xử lý. Cuối luồng, cán bộ ghi hành động và lý do. Nếu một điều kiện bắt buộc thất bại, hệ thống dừng chấm và chuyển hồ sơ sang HOLD.

- **Fast-track cần điều kiện nào?** CS ít nhất 0,75, khoản trả trong khả năng và số tiền trả kỳ khớp điều khoản, sau khi qua các cổng bắt buộc.
- **Có thể chọn một route đang bị khóa không?** API từ chối override nếu route không đủ điều kiện. Fast-track vẫn cần cán bộ xem xét.

## 8. MVP Demo

**Lời nói.** DEMO-001 mua hàng sáu triệu, gồm năm triệu tiền vay và một triệu vốn tự có. Kỳ hạn bốn tháng với lãi suất bằng không cho số tiền trả một triệu hai trăm năm mươi nghìn mỗi tháng. Hệ thống tính hai giới hạn là DTI và phần thu nhập còn lại khi chịu stress. Giới hạn thấp hơn là 2.906.250 đồng. CS khoảng 0,821. Màn hình cho thấy đường fast-track chỉ là một đề xuất để cán bộ kiểm tra.

- **Vì sao số tiền khác bản mockup?** Mockup trang 8 ghi 1,1 triệu. Fixture V2 xác định rõ 5 triệu chia bốn tháng ở lãi suất 0%, ra 1,25 triệu.
- **4,779% và 107.532 đồng trên màn hình là gì?** Điểm logistic với hệ số giả định và phép tính tổn thất mô phỏng. Checkout PD thực tế vẫn null và EL thực tế chưa ước lượng được.

## 9. Feasibility and Business Value

**Lời nói.** Hai phần bằng chứng hiện có là kiểm thử kỹ thuật và benchmark công khai. Trên 4.500 hồ sơ test UCI, XGBoost đạt AUC khoảng 0,785, với khoảng tin cậy 95% từ 0,770 đến 0,801. Đây là khả năng xếp hạng default trong bộ dữ liệu lịch sử. Với ngân hàng, năm chỉ số chi phí, thời gian, chuyển đổi, tổn thất và tải công việc đều chưa đo. Pilot cần nhóm so sánh và dữ liệu trả nợ đủ thời gian quan sát.

- **Nhóm đã giảm được 50% chi phí chưa?** 50% là mục tiêu trong slide gốc. Không có dữ liệu thực nghiệm để báo cáo mức giảm đã đạt.
- **AUC 0,785 có nghĩa là duyệt đúng 78,5% hồ sơ không?** AUC đo khả năng xếp hạng cặp default và không default. Nó không phải accuracy tại ngưỡng duyệt.

## 10. Competitive Advantage

**Lời nói.** Lợi thế có thể chứng minh hôm nay là khả năng lần lại lý do của một đề xuất. Cán bộ thấy dữ liệu nào đã xác minh, phép tính khả năng trả dùng giả định gì và vì sao một đường xử lý đủ điều kiện. Nhật ký lưu phiên bản policy, phiên bản model, dấu vân tay đầu vào và lý do của cán bộ. Còn bên Research Lab, mỗi kết quả gắn với một bộ dữ liệu và checkpoint xác định. Phạm vi so sánh là quy trình trong case HLBVN.

- **COBI có độc nhất trên thị trường không?** Chưa có benchmark đối thủ. Nhóm chỉ đối chiếu các chức năng đã chạy với quy trình được mô tả trong case.
- **Nhật ký có chống sửa tuyệt đối không?** SQLite có trigger chặn sửa hoặc xóa qua ứng dụng. Triển khai thật cần kiểm soát truy cập và cơ chế lưu giữ do ngân hàng phê duyệt.

## A1. Data and Dataset Selection

**Lời nói.** UCI 350 có 30 nghìn bản ghi thẻ tín dụng Đài Loan, với 6.636 trường hợp default tháng kế tiếp. Đầu vào phản ánh lịch sử từ tháng tư đến tháng chín năm 2005. Nhóm khóa bốn tập theo tỷ lệ 60, 15, 10 và 15 phần trăm, dùng seed 42. Chỉ train được dùng để fit bộ chuẩn hóa. Validation chọn mô hình, calibration fit sigmoid và test dành cho đánh giá cuối. Dữ liệu thiếu ngày nộp hồ sơ và khóa khách hàng.

- **Tại sao 19 thành 85?** 13 số tiền chuẩn hóa và sáu trường trạng thái có 12 cột one-hot mỗi trường.
- **Split có phải out-of-time không?** Đây là random stratified holdout. Không có trật tự hồ sơ đáng tin cậy cho OOT hoặc khóa để tách theo khách hàng.

## A2. Mathematical Methods

**Lời nói.** XGBoost xây từng cây nhỏ rồi cộng dự đoán của cây vào log odds hiện tại. Đạo hàm và độ cong của binary log loss hướng dẫn cách tạo cây. Phạt trọng số lá và giới hạn độ sâu giúp kiểm soát độ phức tạp. Learning rate 0,10 làm mỗi cây chỉ đóng góp một phần vào cập nhật. Nhóm chọn theo log loss validation vì đây là bài toán chất lượng xác suất. Bước sigmoid tiếp theo được fit trên một tập riêng.

- **Gradient và Hessian của logistic loss là gì?** Theo margin, chúng lần lượt là p−y và p(1−p).
- **Độ sâu hai bảo đảm hết overfit không?** Nó giới hạn cấu trúc mỗi cây. Bằng chứng chọn đến từ validation và đánh giá test đã khóa.

## A3. Training and Hyperparameter Tuning

**Lời nói.** Ở XGBoost thắng cuộc, vòng 210 có log loss validation tốt nhất. Bộ đếm kiên nhẫn chạy thêm 20 vòng để xem kết quả có cải thiện, nên cấu hình huấn luyện ghi 230 cây. Checkpoint được cắt lại đúng 210 cây. Audit tải checkpoint và so lại đầu ra đã lưu. Logistic dùng LBFGS trên toàn bộ train, còn MLP cập nhật theo minibatch 32, 64 hoặc 128. Vì vậy số vòng giữa các thuật toán có ý nghĩa khác nhau.

- **API thực sự chạy bao nhiêu cây?** 210. Registry và checkpoint có cùng SHA-256. 100 hàng test qua API khớp đầu ra lưu, và tải trực tiếp khớp cả 4.500 hàng.
- **Vì sao tăng giới hạn Logistic từ 1.000 lên 5.000?** C=10 chưa hội tụ ở lần đầu. Lần cuối hội tụ ở 1.268 lượt, trước khi mở test.

## A4. Test Results and Statistical Confidence

**Lời nói.** Trên tập test khóa sẵn, XGBoost có AUC 0,7853 và average precision 0,5738. So với logistic regression, bản thô giảm log loss khoảng 0,01114. Bootstrap ghép cặp lấy lại cùng một tập chỉ số hàng cho cả hai mô hình, rồi tính chênh lệch. Khoảng 95% cho chênh lệch này nằm dưới không. Đây là bằng chứng trên bài toán UCI và phụ thuộc giả định các hàng độc lập, vì không có mã nhóm khách hàng.

- **AP có phải diện tích hình thang dưới PR?** AP là trung bình precision có trọng số theo mức tăng recall. Baseline của test này là tỷ lệ default 22,11%.
- **Khoảng tin cậy có tính đến lần train khác không?** Không. Bootstrap trên dự đoán cố định đo biến động do lấy mẫu hàng của test theo thiết kế này.

## A5. Probability Calibration and Limitations

**Lời nói.** Sigmoid được fit trên ba nghìn bản ghi calibration, tách khỏi test. Vì map tăng đơn điệu trong vùng dự báo quan sát, AUC và average precision giữ nguyên. Log loss lại tăng khoảng 0,000431. Khi bỏ 127 hàng test có vector đầu vào trùng train, ước lượng vẫn tăng nhẹ nhưng khoảng tin cậy đã chứa không. Hai kết quả cùng được trình bày. Nhóm giữ nguyên checkpoint và calibrator đã khóa, vì dùng test để đổi cấu hình sẽ làm sai thiết kế đánh giá.

- **Vì sao fit calibration rồi vẫn có thể tệ hơn?** Hai tham số được tối ưu trên mẫu calibration. Sai số ước lượng hoặc khác biệt phân bố có thể làm map kém phù hợp trên test.
- **Vector giống nhau có phải cùng một người?** Không thể xác định từ dữ liệu. Phân tích loại vector chỉ là độ nhạy hậu nghiệm, không thay cho tách theo khách hàng.

## A6. Explainability and Fairness

**Lời nói.** Audit dùng TreeSHAP trên toàn bộ 4.500 bản ghi validation. Kết quả cộng đóng góp của các cột one-hot về biến gốc, theo đơn vị log odds của mô hình thô. Trạng thái trả nợ tháng chín, PAY_0, đứng đầu theo độ lớn đóng góp trung bình. Hai ví dụ trong phụ lục cho thấy đóng góp có thể khác dấu theo hồ sơ. Kết quả mô tả mô hình đang dựa vào biến nào. Fairness cần đánh giá riêng trên nhóm và dữ liệu được phép.

- **PAY_0 gây ra default hay chỉ liên quan đến dự đoán?** TreeSHAP phân bổ dự đoán đã fit. Nó không xác định tác động nhân quả.
- **Bỏ bốn biến nhân khẩu học đã đủ chứng minh công bằng chưa?** Các biến tài chính có thể đóng vai trò proxy. Cần đo lỗi, calibration và tác động theo nhóm với đủ số sự kiện.

## A7. Business Model and Future Validation

**Lời nói.** Nếu ngân hàng đồng ý, bước đầu là shadow review để cán bộ so kết quả workbench với quy trình đang dùng, trong khi quyền quyết định giữ nguyên. Sau khi kiểm tra rủi ro và dữ liệu, pilot có thể phân nhóm theo đội hoặc cửa hàng để giảm nhiễu giữa hai luồng. Nhóm sẽ đo thời gian, chi phí, chuyển đổi và tải công việc theo cùng mẫu số. Tổn thất tín dụng chỉ được báo cáo sau khi các khoản vay đủ thời gian quan sát và thu hồi.

- **Khi nào có thể nói chi phí giảm?** Khi pilot có nhóm so sánh, chi phí và mẫu số thống nhất, cùng khoảng tin cậy và theo dõi các chỉ số bảo vệ.
- **Vì sao không đo default ngay sau khi rollout?** Nhãn chưa trưởng thành và chỉ quan sát được cho một số quyết định. So sánh sớm sẽ sai thời hạn và có thể lệch mẫu.

## A8. Academic References

**Lời nói.** Các công trình trước đây giúp nhóm chọn thiết kế và hiểu giới hạn. Lessmann cho cơ sở so sánh với logistic. Niculescu-Mizil và Caruana tách chất lượng xác suất khỏi xếp hạng. Wang và Strong cho khung suy nghĩ về chất lượng dữ liệu. Các nghiên cứu về deferral, profit và selective labels nhắc rằng người duyệt, chi phí và cách thu nhãn đều ảnh hưởng kết luận. COBI áp dụng các phương pháp đã có trong prototype và ghi rõ phần nào cần dữ liệu ngân hàng.

- **Nhóm có đề xuất thuật toán học máy mới không?** Đóng góp hiện tại là tích hợp và kiểm chứng quy trình. Boosting, sigmoid, TreeSHAP và bootstrap đều là phương pháp đã công bố.
- **Có thể dùng kết quả profit từ bài báo để tính doanh thu COBI không?** Chỉ dùng để thiết kế tiêu chí. COBI chưa có chi phí, thu hồi, nhãn và dữ liệu pilot phù hợp.
