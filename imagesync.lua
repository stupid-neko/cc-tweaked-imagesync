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

-- Checking local cache
if not fs.exists(file_path) then
    print("Connecting to Pastebin (" .. pastebin_id .. ")...")
    local url = "https://pastebin.com/raw/" .. pastebin_id
    local response, err = http.get(url)

    if not response then
        print("Error while downloading from pastebin...")
        print(err)
        return
    end

    if not fs.exists(dir_path) then fs.makeDir(dir_path) end
    
    print("Saving locally...")
    local file = fs.open(file_path, "w")
    file.write(content)
    file.close()
    response.close()
else
    print("Image found in cache, loading...")
end

-- Read the file (must be added since multiple formats)
local file = fs.open(file_path, "r")
local first_line = file.readLine()
local frameList = {}
local isAnimated = false

-- Read the header (thanks gemini :c)
local w, h, frames, duration = first_line:match("^(%d+),(%d+),(%d+),(%d+)$")

-- If header
if w and h and frames and duration then
    frames = tonumber(frames)
    duration = tonumber(duration) / 1000 --ms
    h = tonumber(h)
    w = tonumber(w)

    if frames > 1 then isAnimated = true end

    -- Read the rest block by block
    for i = 1, frames do
        local frameData = {}
        for j = 1, h do
            frameData[j] = file.readLine()
        end
        frameList[i] = frameData
    end

-- If no header
else
    local frameData = { first_line } -- Keep 1st line as pixels
    local line = file.readLine()
    while line do
        table.insert(frameData, line)
        line = file.readLine()
    end
    frameList[1] = frameData
end
file.close()

-- Render using term.blit (both animated and static)
local function drawFram(lineTable)
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
