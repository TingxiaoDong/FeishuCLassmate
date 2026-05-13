const { feishu_classmate_data_layout, feishu_classmate_temi_status } = require("./tools");
(async () => {
  const layout = await feishu_classmate_data_layout();
  console.log("=== LAYOUT ===");
  console.log(JSON.stringify(layout, null, 2));
  const status = await feishu_classmate_temi_status();
  console.log("=== TEMI STATUS ===");
  console.log(JSON.stringify(status, null, 2));
})();