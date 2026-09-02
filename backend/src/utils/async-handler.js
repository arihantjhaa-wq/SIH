const asyncHandler = (eventHandler) => {
    return (req ,res ,next) => {
        Promise
            .resolve(eventHandler(req , res , next))
            .catch((err) => {next(err)})
    }
}

export {asyncHandler};