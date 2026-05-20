python run_qwen3_5_for_mobile.py \
    --adb_path "/usr/local/bin/adb" \
    --url "https://lpai-llm.lixiang.com/inference/qwen/qwen3.5-397b-a17b/v1/chat/completions" \
    --model "Qwen__Qwen3_5-397B-A17B" \
    --instruction "open 小红书app, browse through feeds, enter the feed for detail note if it is about cars especially EV, take a screenshot for each note and extract the note as json file for record. repeat this loop for 10 times then quit" \
    --no_stream
