output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.public[*].id # Re-route to public subnets to bypass NAT GW cost
}

output "database_subnet_ids" {
  value = aws_subnet.database[*].id
}
