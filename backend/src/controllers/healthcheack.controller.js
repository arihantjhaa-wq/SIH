import { ApiResponse } from "../utils/api-responce.js";
import { asyncHandler } from "../utils/async-handler.js";

const healthCheack = asyncHandler(
    async (req , res) => {
        res.status(200).json(new ApiResponse(200,{message :"Server is running smoothly"}, "Server is healthy"))
    }
)

export {healthCheack};




