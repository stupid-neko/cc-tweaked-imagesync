-- imagesync.lua
local args = {...}
local pastebin_id = args[1]


-- Checking args
if not pastebin_id then
    print("Use     : imagesync <PASTEBIN_ID> ")
    print("Example : imagesync pmF7EYpT")
    return
end

-- Loads monitor
local mon = peripheral.find("monitor")
if not mon then
    print("ERROR: No monitor found !")
    return
end

mon.setTextScale(0.5)
mon.clear()

-- Cache system
local dir_path = "Images"
local file_path = dir_path .. "/" .. pastebin_id .. ".txt"
local content = ""

-- Checking local cache
if fs.exists(file_path) then
    print("Loading cache...")
    local file = fs.open(file_path, "r")
    content = file.readAll()
    file.close()
else
    print("Connecting to Pastebin...")
    local url = "https://pastebin.com/raw/" .. pastebin_id
    local response, err = http.get(url)

    if not response then
        print("Error while downloading from pastebin...")
        print(err)
        return
    end

    content = response.readAll()
    response.close()

    local first_line = content:match("([^\r\n]+)")
    if first_line then
        local w, h, frames, dur = first_line:match("^(%d+),(%d+),(%d+),(%d+)$")
            
        -- Save if static image
        if not frames or tonumber(frames) <= 1 then
            if not fs.exists(dir_path) then fs.makeDir(dir_path) end
            local file = fs.open(file_path, "w")
            file.write(content)
            file.close()
            print("Saved static image to cache.")
        else
            print("GIF detected: Skipping cache to save disk space.")
        end
    end
end

-- Content analysis
local lines = {}
for line in content:gmatch("[^\r\n]+") do
    table.insert(lines, line)
end
local first_line = lines[1]
local frameList = {}
local isAnimated = false

-- Read the header (thanks gemini :c)
local w, h, frames, duration = first_line:match("^(%d+),(%d+),(%d+),(%d+)$")

-- If header
if w and h and frames and duration then
    frames = tonumber(frames)
    duration = tonumber(duration) / 1000 --ms
    h = tonumber(h)
    w = tonumber(w)  -- useless :(

    if frames > 1 then isAnimated = true end

    -- Read the rest block by block
    for i = 1, frames do
        local frameData = {}
        for j = 1, h do
            frameData[j] = lines[((i-1) * h + j) + 1]
        end
        frameList[i] = frameData
    end

-- If no header
else
    frameList[1] = lines
end

-- Render using term.blit (both animated and static)
local function drawFrame(linesTable)
    for y = 1, #linesTable do
        local line = linesTable[y]
        if line and #line > 0 then
            mon.setCursorPos(1, y)
            local empty_text = string.rep(" ", #line)
            local text_color = string.rep("f", #line)  -- Text is empty...
            mon.blit(empty_text, text_color, line)
        end
    end
end

-- Display logic here
if isAnimated then
    print("Playing GIF, press any key to stop")

    local currentFrame = 1
    local timerId = os.startTimer(duration)

    -- Inf loop
    while true do
        local event, p1 = os.pullEvent()

        -- When its time to draw the next frame
        if event == "timer" and p1 == timerId then
            drawFrame(frameList[currentFrame])
            currentFrame = currentFrame + 1

            if currentFrame > frames then currentFrame = 1 end -- Loop back to start

            timerId = os.startTimer(duration) -- Wait for next frame
        
        elseif event == "key" or event == "char" then   -- Add redstone or modem signals
            print("Stopping animation...")
            break
        end
    end
else  -- Static ez
    drawFrame(frameList[1])
    print("Task should be done")
end
