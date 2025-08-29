output "image_uri" {
  value = data.aws_ecr_image.lambda_image.image_uri
}