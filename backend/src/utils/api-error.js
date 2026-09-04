class ApiError extends Error{
    constructor(
        statusCode,
        message ="Somthing is not good",
        errors =[],
        stack = '',
    ){
        super(message)  //Calling the constructor of parant class
         this.statusCode=statusCode 
        this.data =null 
        this.message = message
        this.success = false
        this.errors = errors

        if(stack){
            this.stack = stack
        }else{
            Error.captureStackTrace(this, this.constructor);
        }

    }
      
}

export {ApiError};