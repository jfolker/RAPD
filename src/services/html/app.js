const express = require('express')
const app = express()

app.use('/', express.static('../../ui/dist'));

app.listen(4200, () => console.log('Example app listening on port 4200!'))
